"""
Élévation et pente dérivées du SRTM.

Dataset : USGS/SRTMGL1_003 (30 m natif)
Sortie : reprojetée à export_scale (1 000 m par défaut)
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target


def get_dem_layers(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Retourne l'élévation (m) et la pente (degrés) reprojetées sur la grille cible.

    La pente est calculée via ``ee.Terrain.slope`` sur le MNT SRTM.

    Parameters
    ----------
    aoi : ee.Geometry
        Zone d'intérêt.
    config : dict
        Section `gee` de la configuration.

    Returns
    -------
    ee.Image
        Bandes : elevation, slope
    """
    cfg = config["dem"]

    dem = (
        ee.Image(cfg["collection"])
        .select(cfg["elevation_band"])
        .rename("elevation")
        .clip(aoi)
    )
    slope = ee.Terrain.slope(dem).rename("slope")
    stacked = dem.addBands(slope)

    return reproject_to_target(stacked, config)