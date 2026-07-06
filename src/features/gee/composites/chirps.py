"""
Précipitations CHIRPS — agrégations alignées sur DHS 2018.

Dataset : UCSB-CHG/CHIRPS/DAILY
Bande   : precipitation (mm/jour)
Résolution native : ~0,05° (~5,5 km)

Features produites (bandes GEE internes) :
  - precip_annual  : somme annuelle (mm)
  - precip_wet     : somme saison humide (mm)
  - precip_cv      : coefficient de variation intra-annuel (std / mean)

La moyenne dans reduceRegions sur les buffers DHS donne la valeur
moyenne par grappe à la résolution export_scale (1 km).
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target

CHIRPS_FEATURE_COLUMNS = frozenset({
    "precip_annual_mm",
    "precip_wet_season_mm",
    "precip_cv",
})


def get_chirps_collection(aoi: ee.Geometry, config: dict) -> ee.ImageCollection:
    """Filtre la collection CHIRPS daily sur l'AOI et la fenêtre temporelle."""
    cfg = config["chirps"]
    return (
        ee.ImageCollection(cfg["collection"])
        .filterBounds(aoi)
        .filterDate(cfg["start"], cfg["end"])
        .select(cfg.get("band", "precipitation"))
    )


def get_chirps_composite(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Construit le composite CHIRPS reprojeté à export_scale.

    Parameters
    ----------
    aoi : ee.Geometry
        Zone d'intérêt.
    config : dict
        Section `gee` de configs/gee.yaml (clé `chirps` requise).

    Returns
    -------
    ee.Image
        Bandes : precip_annual, precip_wet, precip_cv
    """
    cfg = config["chirps"]
    collection = get_chirps_collection(aoi, config)

    annual_sum = collection.sum().rename("precip_annual")

    wet_start = int(cfg["wet_season_start_month"])
    wet_end = int(cfg["wet_season_end_month"])
    wet_collection = collection.filter(
        ee.Filter.calendarRange(wet_start, wet_end, "month")
    )
    wet_sum = wet_collection.sum().rename("precip_wet")

    mean_daily = collection.mean()
    std_daily = collection.reduce(ee.Reducer.stdDev())
    # CV = std / mean ; 0 si moyenne nulle (zones très sèches)
    cv = (
        std_daily
        .divide(mean_daily.max(1e-6))
        .rename("precip_cv")
    )

    stacked = annual_sum.addBands(wet_sum).addBands(cv)
    return reproject_to_target(stacked.clip(aoi), config)


def uses_chirps_features(config: dict) -> bool:
    """Indique si le jeu de features actif inclut des colonnes CHIRPS."""
    return bool(CHIRPS_FEATURE_COLUMNS & set(config.get("feature_columns", [])))