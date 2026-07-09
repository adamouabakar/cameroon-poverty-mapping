"""
Assemblage de l'image multi-bandes de features pour la modélisation.
"""
from __future__ import annotations

import ee

from src.features.gee.composites.chirps import get_chirps_composite, uses_chirps_features
from src.features.gee.composites.dem import get_dem_layers
from src.features.gee.composites.ghsl import get_ghsl_image
from src.features.gee.composites.landcover import get_built_density
from src.features.gee.composites.osm import get_osm_distances
from src.features.gee.composites.sentinel2 import get_s2_composite
from src.features.gee.composites.viirs import get_viirs_composite
from src.features.gee.composites.worldpop import get_worldpop
from src.features.gee.projection import reproject_to_target

QA_BANDS = ["ndwi", "evi"]


def _get_built_layer(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Choisit GHSL ou WorldCover selon les colonnes actives dans la config.

    La source de vérité est feature_columns pour éviter un décalage config/stack.
    """
    if "ghsl_built_fraction" in config["feature_columns"]:
        return get_ghsl_image(aoi, config)
    return get_built_density(aoi, config)


def build_feature_image(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Construit une image multi-bandes alignée sur EPSG:32633 @ export_scale.

    v1  : WorldCover built_density
    v2  : GHSL ghsl_built_fraction
    v3  : v2 + CHIRPS (precip_annual, precip_wet, precip_cv)
    """
    s2 = get_s2_composite(aoi, config)
    viirs = get_viirs_composite(aoi, config)
    dem = get_dem_layers(aoi, config)
    pop = get_worldpop(aoi, config)
    built = _get_built_layer(aoi, config)
    osm = get_osm_distances(aoi, config)

    stacked = (
        s2.addBands(viirs)
        .addBands(dem)
        .addBands(pop)
        .addBands(built)
        .addBands(osm)
    )

    if uses_chirps_features(config):
        stacked = stacked.addBands(get_chirps_composite(aoi, config))

    stacked = stacked.clip(aoi)
    # Export GEE exige des types homogènes (évite Float64/Float32 mixtes).
    return reproject_to_target(stacked, config).toFloat()


def get_model_bands(config: dict) -> list[str]:
    return [config["band_names"][col] for col in config["feature_columns"]]


def get_model_bands_legacy() -> list[str]:
    return [
        "night_lights",
        "ndvi",
        "ndbi",
        "dist_road_m",
        "dist_school_m",
        "dist_health_m",
        "pop_density",
        "elevation",
        "slope",
        "built_density",
    ]