"""
Surface bâtie GHSL GHS-BUILT-S (Sentinel-2 + Landsat, R2023A).

Dataset : JRC/GHSL/P2023A/GHS_BUILT_S
Epoch par défaut : 2015 (la plus proche de DHS 2018 parmi les pas de 5 ans)

La bande `built_surface` exprime la surface bâtie en m² par pixel 100 m.
On la normalise en fraction [0, 1] par rapport à la surface du pixel (10 000 m²).
La moyenne dans reduceRegions donne la fraction de surface bâtie dans le buffer.
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target

_DEFAULT_CELL_AREA_M2 = 10_000


def get_ghsl_raw_image(aoi: ee.Geometry, config: dict) -> ee.Image:
    """Charge la bande built_surface (m²) pour l'epoch configurée."""
    cfg = config["ghsl"]
    year = int(cfg["epoch_year"])
    asset_id = f"{cfg['collection']}/{year}"
    band = cfg.get("band", "built_surface")
    return ee.Image(asset_id).select(band).clip(aoi)


def get_ghsl_image(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Retourne la fraction de surface bâtie GHSL reprojetée à export_scale.

    Bande de sortie : `ghsl_built` (fraction [0, 1]).
    Doit correspondre à band_names.ghsl_built_fraction dans configs/gee.yaml.
    """
    cfg = config["ghsl"]
    cell_area = float(cfg.get("cell_area_m2", _DEFAULT_CELL_AREA_M2))

    built_m2 = get_ghsl_raw_image(aoi, config)
    fraction = (
        built_m2
        .divide(cell_area)
        .clamp(0, 1)
        .rename("ghsl_built")
    )
    return reproject_to_target(fraction, config)