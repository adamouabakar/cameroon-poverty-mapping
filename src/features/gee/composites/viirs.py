"""
Composite VIIRS Nighttime Lights (VNP46A2).

Dataset : NASA/VIIRS/002/VNP46A2 (remplace NOAA/VIIRS/001 déprécié)
Période : 2018 (alignée sur DHS 2018)
Composite : médiane après masquage qualité (flags 0 et 1)
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target


def _quality_clear_values(cfg: dict) -> list[int]:
    """Retourne les valeurs Mandatory_Quality_Flag acceptées."""
    if "quality_clear_values" in cfg:
        return [int(v) for v in cfg["quality_clear_values"]]
    return [int(cfg["quality_clear_value"])]


def _quality_mask(quality: ee.Image, cfg: dict) -> ee.Image:
    """Masque pixels de bonne qualité (persistent + ephemeral pour NASA/002)."""
    mask = None
    for value in _quality_clear_values(cfg):
        m = quality.eq(value)
        mask = m if mask is None else mask.Or(m)
    return mask


def _mask_viirs_quality(image: ee.Image, config: dict) -> ee.Image:
    """
    Conserve les pixels de bonne qualité selon Mandatory_Quality_Flag.

    NASA/002 : 0 = persistent, 1 = ephemeral (les deux sont haute qualité).
    """
    cfg = config["viirs"]
    quality = image.select(cfg["quality_band"])
    ntl = image.select(cfg["band"])
    return ntl.updateMask(_quality_mask(quality, cfg)).rename("night_lights")


def get_viirs_collection(aoi: ee.Geometry, config: dict) -> ee.ImageCollection:
    """
    Filtre la collection VIIRS VNP46A2 sur l'AOI et la période 2018.

    Returns
    -------
    ee.ImageCollection
        Collection avec bandes NTL + qualité.
    """
    cfg = config["viirs"]
    temporal = config["temporal"]

    return (
        ee.ImageCollection(cfg["collection"])
        .filterBounds(aoi)
        .filterDate(temporal["viirs_start"], temporal["viirs_end"])
        .select([cfg["band"], cfg["quality_band"]])
    )


def get_viirs_composite(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Produit un composite de luminosité nocturne reprojeté à 1 km.

    Pipeline :
      1. Filtrage spatial / temporel
      2. Masquage qualité pixel par pixel
      3. Réduction temporelle (médiane par défaut)
      4. Reprojection EPSG:32633 @ export_scale

    Returns
    -------
    ee.Image
        Bande unique : night_lights
    """
    cfg = config["viirs"]
    collection = get_viirs_collection(aoi, config)
    masked = collection.map(lambda img: _mask_viirs_quality(img, config))

    method = cfg.get("composite_method", "median").lower()
    composite = masked.mean() if method == "mean" else masked.median()

    return reproject_to_target(composite.rename("night_lights"), config)