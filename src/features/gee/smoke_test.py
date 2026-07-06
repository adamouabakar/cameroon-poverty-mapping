"""
Smoke test local pour valider les composites GEE sur la bbox Yaoundé.

Usage (depuis la racine du projet) :

    python -m src.features.gee.smoke_test
"""

from __future__ import annotations

from typing import Any

import ee

from src.features.gee.client import get_test_aoi, initialize_from_config
from src.features.gee.composites.dem import get_dem_layers
from src.features.gee.composites.sentinel2 import get_s2_composite
from src.features.gee.composites.viirs import get_viirs_composite


def sample_image_at_center(
    image: ee.Image,
    geometry: ee.Geometry,
    scale: int,
    band_names: list[str],
) -> dict[str, float | None]:
    """
    Échantillonne les bandes d'une image au centroïde de la géométrie.

    Parameters
    ----------
    image : ee.Image
        Image à échantillonner.
    geometry : ee.Geometry
        Zone d'intérêt (bbox de test).
    scale : int
        Résolution d'échantillonnage en mètres.
    band_names : list[str]
        Noms des bandes à extraire.

    Returns
    -------
    dict
        Valeurs par bande au point central (None si masqué).
    """
    point = geometry.centroid(maxError=1)
    sampled = (
        image.select(band_names)
        .reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=scale,
            maxPixels=int(1e9),
        )
        .getInfo()
    )
    return {band: sampled.get(band) for band in band_names}


def run_yaounde_smoke_test(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Construit S2 + VIIRS + DEM sur la bbox Yaoundé et échantillonne le centre.

    Parameters
    ----------
    config : dict, optional
        Section `gee`. Si None, charge configs/gee.yaml et initialise EE.

    Returns
    -------
    dict
        Rapport avec AOI, bandes échantillonnées et statut.
    """
    if config is None:
        _, config = initialize_from_config()

    aoi = get_test_aoi(config)
    scale = int(config["export_scale"])

    s2 = get_s2_composite(aoi, config)
    viirs = get_viirs_composite(aoi, config)
    dem = get_dem_layers(aoi, config)

    report: dict[str, Any] = {
        "aoi": config["test_aoi"],
        "scale_m": scale,
        "crs": config["crs"],
        "samples": {},
    }

    report["samples"]["sentinel2"] = sample_image_at_center(
        s2, aoi, scale, ["ndvi", "ndbi", "ndwi", "evi"]
    )
    report["samples"]["viirs"] = sample_image_at_center(
        viirs, aoi, scale, ["night_lights"]
    )
    report["samples"]["dem"] = sample_image_at_center(
        dem, aoi, scale, ["elevation", "slope"]
    )

    report["status"] = "ok"
    return report


def main() -> None:
    """Point d'entrée CLI pour le smoke test Yaoundé."""
    import json

    report = run_yaounde_smoke_test()
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()