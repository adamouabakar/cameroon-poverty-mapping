"""
Fraction de surface bâtie via ESA WorldCover.

Dataset : ESA/WorldCover/v200 (2021)
Classe 50 = Built-up

Limitation documentée : décalage temporel ~3 ans vs DHS 2018.
La moyenne du masque binaire dans un buffer ≈ fraction built-up [0, 1].
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target


def get_worldcover_image(aoi: ee.Geometry, config: dict) -> ee.Image:
    """Charge la classification WorldCover (ImageCollection v200) et clippe l'AOI."""
    cfg = config["landcover"]
    return (
        ee.ImageCollection(cfg["collection"])
        .first()
        .select("Map")
        .clip(aoi)
    )


def get_built_density(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Retourne un masque binaire built-up (0/1) reprojeté à export_scale.

    Returns
    -------
    ee.Image
        Bande `built_density` : 1 = bâti, 0 = autre.
        La moyenne dans reduceRegions donne la fraction de surface bâtie.
    """
    cfg = config["landcover"]
    worldcover = get_worldcover_image(aoi, config)
    built = worldcover.eq(cfg["built_class"]).rename("built_density")
    return reproject_to_target(built, config)