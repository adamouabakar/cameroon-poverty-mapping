"""
Densité de population WorldPop.

Dataset : WorldPop/GP/100m/pop
Année : 2018 (alignée sur DHS 2018)
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target


def get_worldpop_collection(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Charge l'image WorldPop pour l'année configurée.

    Returns
    -------
    ee.Image
        Bande population (personnes par pixel 100 m natif).
    """
    cfg = config["worldpop"]
    year = int(config["temporal"]["worldpop_year"])

    collection = (
        ee.ImageCollection(cfg["collection"])
        .filterBounds(aoi)
        .filter(ee.Filter.calendarRange(year, year, "year"))
    )

    # Plusieurs tuiles peuvent couvrir l'AOI pour une même année → mosaic
    image = (
        collection.mosaic()
        .select(cfg["band"])
        .rename("pop_density")
        .unmask(0)
    )
    return image.clip(aoi)


def get_worldpop(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Retourne la densité de population reprojetée à export_scale.

    Note : WorldPop natif = 100 m ; la moyenne à 1 km via reduceRegions
    donne une population moyenne par pixel 1 km (à interpréter comme
    densité relative, pas comptage exact).
    """
    image = get_worldpop_collection(aoi, config)
    return reproject_to_target(image, config)