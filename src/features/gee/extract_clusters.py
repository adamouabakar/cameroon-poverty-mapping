"""Extraction reduceRegions sur les buffers des grappes DHS."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.features.gee.clusters import gdf_to_ee_fc
from src.features.gee.postprocess import features_to_model_schema
from src.features.gee.qa import validate_features
from src.features.gee.stack import build_feature_image

try:
    import ee
except ImportError:  # pragma: no cover
    ee = None


def _reduction_bands(config: dict) -> list[str]:
    """Bandes GEE à extraire : features modèle + QA (ndwi, evi)."""
    bands = [config["band_names"][col] for col in config["feature_columns"]]
    bands.extend(["ndwi", "evi"])
    return list(dict.fromkeys(bands))


def _expected_built_band(config: dict) -> str:
    """Bande bâti attendue dans le stack selon feature_columns."""
    if "ghsl_built_fraction" in config["feature_columns"]:
        return config["band_names"]["ghsl_built_fraction"]
    return config["band_names"]["built_density"]


def extract_features_for_clusters(
    feature_image: "ee.Image",
    clusters_gdf: gpd.GeoDataFrame,
    config: dict,
    run_qa: bool = True,
) -> pd.DataFrame:
    """
    Applique reduceRegions (mean) sur les polygones de grappes.
    Retourne un DataFrame avec cluster_id + 10 features.
    """
    if ee is None:
        raise ImportError("earthengine-api est requis pour l'extraction GEE.")

    fc = gdf_to_ee_fc(clusters_gdf)
    bands = _reduction_bands(config)

    # Garde-fou : évite l'erreur GEE opaque "Band pattern 'ghsl_built' did not match"
    built_band = _expected_built_band(config)
    if built_band not in bands:
        raise ValueError(
            f"Bande bâti '{built_band}' absente du mapping band_names. "
            f"Colonnes actives : {config['feature_columns']}"
        )

    image = feature_image.select(bands)

    reducer = ee.Reducer.mean()
    scale = config["export_scale"]
    tile_scale = config.get("tile_scale", 4)

    reduced = image.reduceRegions(
        collection=fc,
        reducer=reducer,
        scale=scale,
        crs=config["crs"],
        tileScale=tile_scale,
    )

    rows = reduced.getInfo()["features"]
    records = []
    for feat in rows:
        props = feat["properties"]
        records.append(props)

    raw_df = pd.DataFrame(records)
    model_df = features_to_model_schema(raw_df, config)

    model_df = _impute_missing_features(model_df, config)

    if run_qa:
        validate_features(model_df, config["feature_columns"])

    return model_df


def _impute_missing_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Remplace les NaN résiduels après reduceRegions (zones côtières, nuages, etc.).

    Stratégie documentée dans documentation/gee_features.md :
    - luminosité / population / indices / élévation → 0
    - distances → plafond OSM configuré (km)

    À réévaluer avec les vraies grappes DHS : préférer journaliser les imputations
    plutôt que masquer silencieusement les trous de couverture.
    """
    out = df.copy()
    max_dist_km = int(config["osm"].get("max_distance_m", 50000)) / 1000.0
    defaults = {
        "night_lights_mean": 0.0,
        "ndvi_mean": 0.0,
        "ndbi_mean": 0.0,
        "pop_density": 0.0,
        "elevation_m": 0.0,
        "slope_deg": 0.0,
        "built_density": 0.0,
        "ghsl_built_fraction": 0.0,
        "precip_annual_mm": 1600.0,
        "precip_wet_season_mm": 1400.0,
        "precip_cv": 0.8,
        "dist_road_km": max_dist_km,
        "dist_school_km": max_dist_km,
        "dist_health_km": max_dist_km,
    }
    for col in config["feature_columns"]:
        if col in out.columns:
            out[col] = out[col].fillna(defaults.get(col, 0.0))
    return out


def _resolve_extraction_aoi(
    clusters_gdf: gpd.GeoDataFrame,
    config: dict,
    mode: str,
    aoi_geometry=None,
) -> tuple:
    """
    Choisit l'AOI du stack :
    - test   : bbox Yaoundé ou emprise des grappes (données fictives)
    - clusters : emprise des grappes (+ marge)
    - national : géométrie LSIB Cameroun (export raster)
    """
    from src.features.gee.aoi import get_aoi_geometry, get_test_bbox_geometry

    if aoi_geometry is not None:
        return aoi_geometry, "custom"

    if mode == "clusters":
        return _clusters_bounds_geometry(clusters_gdf), "clusters_bounds"

    if mode == "national":
        return get_aoi_geometry(config, mode="national"), "national"

    west, south, east, north = config["test_aoi"]["bbox"]
    gdf_wgs = clusters_gdf.to_crs(epsg=4326)
    in_bbox = gdf_wgs.cx[west:east, south:north]
    if len(in_bbox) > 0:
        return get_test_bbox_geometry(config), "yaounde_test"

    # Données fictives hors Yaoundé : AOI = emprise des grappes (+ marge)
    return _clusters_bounds_geometry(clusters_gdf), "clusters_bounds"


def extract_from_clusters_file(
    clusters_path: str | Path,
    config: dict,
    mode: str = "test",
    aoi_geometry=None,
) -> pd.DataFrame:
    """Pipeline complet : AOI → stack → reduceRegions → QA."""
    clusters_gdf = gpd.read_parquet(clusters_path)

    if mode == "test":
        clusters_gdf = _filter_clusters_to_test_bbox(clusters_gdf, config)

    aoi, aoi_label = _resolve_extraction_aoi(clusters_gdf, config, mode, aoi_geometry)
    feature_image = build_feature_image(aoi, config)
    result = extract_features_for_clusters(feature_image, clusters_gdf, config)
    result.attrs["aoi_used"] = aoi_label
    return result


def _clusters_bounds_geometry(
    gdf: gpd.GeoDataFrame,
    margin_deg: float = 0.25,
) -> "ee.Geometry":
    """Rectangle englobant les grappes avec une marge (degrés)."""
    import ee

    gdf_wgs = gdf.to_crs(epsg=4326)
    minx, miny, maxx, maxy = gdf_wgs.total_bounds
    return ee.Geometry.Rectangle(
        [minx - margin_deg, miny - margin_deg, maxx + margin_deg, maxy + margin_deg]
    )


def _filter_clusters_to_test_bbox(
    gdf: gpd.GeoDataFrame, config: dict
) -> gpd.GeoDataFrame:
    """Conserve les grappes dans la bbox de test (Yaoundé par défaut)."""
    west, south, east, north = config["test_aoi"]["bbox"]
    gdf_wgs = gdf.to_crs(epsg=4326)
    filtered = gdf_wgs.cx[west:east, south:north]
    if len(filtered) == 0:
        return gdf_wgs.head(min(10, len(gdf_wgs)))
    return filtered