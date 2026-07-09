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