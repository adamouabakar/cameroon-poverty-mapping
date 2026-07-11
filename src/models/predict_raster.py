"""
Inférence LightGBM sur une grille raster (stack de features GeoTIFF).

Prérequis : export national GEE des 13 bandes v3 (voir scripts/extract_gee_features.py --mode national).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from src.data.wealth_scaling import WealthScaler, load_scaler
from src.ins.regions import INS_FEATURE_COLUMNS_V4, harmonize_region_name
from src.models.save_load import load_model


def _band_to_column_map(config: dict) -> dict[str, str]:
    """Bande GEE → colonne modèle."""
    return {band: col for col, band in config["band_names"].items()}


def _impute_defaults(config: dict) -> dict[str, float]:
    max_dist = int(config["osm"].get("max_distance_m", 50000)) / 1000.0
    return {
        "night_lights_mean": 0.0,
        "ndvi_mean": 0.0,
        "ndbi_mean": 0.0,
        "pop_density": 0.0,
        "elevation_m": 0.0,
        "slope_deg": 0.0,
        "ghsl_built_fraction": 0.0,
        "precip_annual_mm": 1600.0,
        "precip_wet_season_mm": 1400.0,
        "precip_cv": 0.8,
        "dist_road_km": max_dist,
        "dist_school_km": max_dist,
        "dist_health_km": max_dist,
    }


def predict_wealth_raster(
    feature_raster_path: str | Path,
    model_path: str | Path,
    output_path: str | Path,
    config: dict,
    *,
    chunk_size: int = 512,
    nodata: float = -9999.0,
    scaler_path: str | Path | None = None,
    output_raw_path: str | Path | None = None,
) -> Path:
    """
    Lit un GeoTIFF multi-bandes, prédit wealth_index pixel à pixel par chunks.
    """
    model = load_model(model_path)
    scaler: WealthScaler | None = None
    if scaler_path and Path(scaler_path).exists():
        scaler = load_scaler(scaler_path)
    feature_cols = config["feature_columns"]
    band_map = _band_to_column_map(config)
    defaults = _impute_defaults(config)
    dist_bands = {"dist_road_m", "dist_school_m", "dist_health_m"}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path = Path(output_raw_path) if output_raw_path else None
    if raw_path:
        raw_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(feature_raster_path) as src:
        profile = src.profile.copy()
        profile.update(count=1, dtype="float32", nodata=nodata)

        band_idx = {}
        for i in range(1, src.count + 1):
            name = src.descriptions[i - 1] if src.descriptions[i - 1] else None
            if name:
                band_idx[name] = i

        if len(band_idx) < len(feature_cols):
            export_bands = [config["band_names"][col] for col in feature_cols]
            for i, name in enumerate(export_bands, start=1):
                if i <= src.count:
                    band_idx.setdefault(name, i)

        dst_raw = rasterio.open(raw_path, "w", **profile) if raw_path else None
        with rasterio.open(output_path, "w", **profile) as dst:
            for ji in range(0, src.height, chunk_size):
                h = min(chunk_size, src.height - ji)
                for ii in range(0, src.width, chunk_size):
                    w = min(chunk_size, src.width - ii)
                    window = rasterio.windows.Window(ii, ji, w, h)

                    data = {}
                    for col in feature_cols:
                        band_name = config["band_names"][col]
                        if band_name not in band_idx:
                            raise KeyError(f"Bande {band_name} absente du raster.")
                        arr = src.read(band_idx[band_name], window=window).astype(np.float32)
                        if band_name in dist_bands:
                            arr = arr / 1000.0
                        data[col] = arr.ravel()

                    X = pd.DataFrame(data)
                    for col in feature_cols:
                        X[col] = X[col].fillna(defaults.get(col, 0.0))

                    pred = model.predict(X).reshape(h, w).astype(np.float32)
                    pred[~np.isfinite(pred)] = nodata
                    dst.write(pred, 1, window=window)
                    if dst_raw is not None and scaler is not None:
                        pred_raw = scaler.inverse_transform(pred.ravel()).reshape(h, w).astype(np.float32)
                        pred_raw[~np.isfinite(pred_raw)] = nodata
                        dst_raw.write(pred_raw, 1, window=window)

        if dst_raw is not None:
            dst_raw.close()

    return output_path


def _load_ins_lookup(ins_parquet_path: str | Path) -> tuple[dict[str, dict[str, float]], list[str]]:
    """Construit un dictionnaire région DHS → valeurs INS (v4)."""
    ins = pd.read_parquet(ins_parquet_path)
    ins["region_dhs"] = harmonize_region_name(ins["region_dhs"])
    rename = {
        "poverty_rate_pct": "ins_poverty_rate_pct",
        "literacy_rate_15plus_pct": "ins_literacy_rate_15plus_pct",
        "electricity_access_pct": "ins_electricity_access_pct",
        "primary_enrollment_pct": "ins_primary_enrollment_pct",
    }
    ins = ins.rename(columns=rename)
    lookup: dict[str, dict[str, float]] = {}
    for _, row in ins.iterrows():
        region = row["region_dhs"]
        lookup[region] = {col: float(row[col]) for col in INS_FEATURE_COLUMNS_V4}
    regions = sorted(lookup.keys())
    return lookup, regions


def _build_region_kdtree(clusters_gdf, target_crs: str):
    """Arbre KD sur centroïdes de grappes pour assigner une région par pixel."""
    from scipy.spatial import cKDTree

    pts = clusters_gdf.to_crs(target_crs)
    centroids = np.column_stack(
        [pts.geometry.centroid.x.to_numpy(), pts.geometry.centroid.y.to_numpy()]
    )
    regions = harmonize_region_name(pts["region"]).tolist()
    return cKDTree(centroids), regions


def _ins_arrays_for_regions(
    regions: list[str],
    ins_lookup: dict[str, dict[str, float]],
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    """Tableaux indexés par region_id pour remplissage vectorisé."""
    region_to_id = {r: i for i, r in enumerate(regions)}
    arrays = {
        col: np.array([ins_lookup[r][col] for r in regions], dtype=np.float32)
        for col in INS_FEATURE_COLUMNS_V4
    }
    return arrays, region_to_id


def predict_wealth_raster_v4(
    feature_raster_path: str | Path,
    model_path: str | Path,
    output_path: str | Path,
    gee_config: dict,
    *,
    clusters_path: str | Path,
    ins_parquet_path: str | Path,
    chunk_size: int = 512,
    nodata: float = -9999.0,
) -> Path:
    """
    Inférence v4 : bandes GEE v3 + variables INS régionales (ECAM 4).

    La région INS par pixel est déduite de la grappe DHS la plus proche
    (proxy en l'absence de découpage administratif rasterisé).
    """
    import geopandas as gpd

    model = load_model(model_path)
    feature_cols = list(gee_config["feature_columns"]) + list(INS_FEATURE_COLUMNS_V4)
    gee_cols = list(gee_config["feature_columns"])
    band_map = _band_to_column_map(gee_config)
    defaults = _impute_defaults(gee_config)
    dist_bands = {"dist_road_m", "dist_school_m", "dist_health_m"}

    ins_lookup, region_list = _load_ins_lookup(ins_parquet_path)
    ins_arrays, region_to_id = _ins_arrays_for_regions(region_list, ins_lookup)

    clusters = gpd.read_parquet(clusters_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(feature_raster_path) as src:
        tree, cluster_regions = _build_region_kdtree(clusters, str(src.crs))
        cluster_region_ids = np.array(
            [region_to_id.get(r, 0) for r in cluster_regions], dtype=np.int32
        )

        profile = src.profile.copy()
        profile.update(count=1, dtype="float32", nodata=nodata)

        band_idx: dict[str, int] = {}
        for i in range(1, src.count + 1):
            name = src.descriptions[i - 1] if src.descriptions[i - 1] else None
            if name:
                band_idx[name] = i
        if len(band_idx) < len(gee_cols):
            for col in gee_cols:
                band_name = gee_config["band_names"][col]
                if band_name not in band_idx:
                    for i in range(1, src.count + 1):
                        desc = src.descriptions[i - 1]
                        if desc == band_name:
                            band_idx[band_name] = i

        with rasterio.open(output_path, "w", **profile) as dst:
            for ji in range(0, src.height, chunk_size):
                h = min(chunk_size, src.height - ji)
                for ii in range(0, src.width, chunk_size):
                    w = min(chunk_size, src.width - ii)
                    window = rasterio.windows.Window(ii, ji, w, h)

                    data: dict[str, np.ndarray] = {}
                    for col in gee_cols:
                        band_name = gee_config["band_names"][col]
                        if band_name not in band_idx:
                            raise KeyError(f"Bande {band_name} absente du raster.")
                        arr = src.read(band_idx[band_name], window=window).astype(np.float32)
                        if band_name in dist_bands:
                            arr = arr / 1000.0
                        data[col] = arr.ravel()

                    rows = np.arange(ji, ji + h)
                    cols = np.arange(ii, ii + w)
                    cc, rr = np.meshgrid(cols, rows)
                    xs, ys = rasterio.transform.xy(
                        src.transform, rr.ravel(), cc.ravel(), offset="center"
                    )
                    coords = np.column_stack([xs, ys]).astype(np.float64)
                    _, nearest = tree.query(coords)
                    region_ids = cluster_region_ids[nearest]

                    for col in INS_FEATURE_COLUMNS_V4:
                        data[col] = ins_arrays[col][region_ids]

                    X = pd.DataFrame(data)
                    for col in feature_cols:
                        X[col] = X[col].fillna(defaults.get(col, 0.0))

                    pred = model.predict(X).reshape(h, w).astype(np.float32)
                    pred[~np.isfinite(pred)] = nodata
                    dst.write(pred, 1, window=window)

    return output_path