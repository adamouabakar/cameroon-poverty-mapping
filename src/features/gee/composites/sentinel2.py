"""
Composite Sentinel-2 SR harmonisé et indices spectraux.

Dataset : COPERNICUS/S2_SR_HARMONIZED
Période : 2017–2019 (configurable)
Composite : médiane temporelle (robuste aux nuages résiduels)
"""

from __future__ import annotations

import ee

from src.features.gee.projection import reproject_to_target

# Bandes de réflectance utilisées pour les indices
S2_REFLECTANCE_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]

# Bandes exportées pour la modélisation (Phase 1)
S2_FEATURE_BANDS = ["ndvi", "ndbi"]

# Bandes supplémentaires pour QA interne
S2_QA_BANDS = ["ndwi", "evi"]


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    """
    Masque les pixels nuageux et cirrus via la bande QA60.

    Bits 10 (nuages opaques) et 11 (cirrus) doivent être à 0.
    """
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = (
        qa.bitwiseAnd(cloud_bit)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus_bit).eq(0))
    )
    return image.updateMask(mask)


def get_s2_collection(aoi: ee.Geometry, config: dict) -> ee.ImageCollection:
    """
    Filtre la collection Sentinel-2 SR sur l'AOI, la période et le couvert nuageux.

    Parameters
    ----------
    aoi : ee.Geometry
        Zone d'intérêt.
    config : dict
        Section `gee` de la configuration.

    Returns
    -------
    ee.ImageCollection
        Collection filtrée, non encore compositée.
    """
    cfg = config["sentinel2"]
    temporal = config["temporal"]

    collection = (
        ee.ImageCollection(cfg["collection"])
        .filterBounds(aoi)
        .filterDate(temporal["sentinel2_start"], temporal["sentinel2_end"])
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cfg["cloud_cover_max"]))
        .select(S2_REFLECTANCE_BANDS + ["QA60"])
    )

    if cfg.get("apply_qa_cloud_mask", True):
        collection = collection.map(mask_s2_clouds)

    return collection


def add_spectral_indices(image: ee.Image) -> ee.Image:
    """
    Calcule NDVI, NDBI, NDWI et EVI à partir de la réflectance surface.

    NDVI = (NIR - RED) / (NIR + RED)           → végétation
    NDBI = (SWIR - NIR) / (SWIR + NIR)         → zones bâties
    NDWI = (GREEN - NIR) / (GREEN + NIR)       → eau / humidité
    EVI  = 2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)
    """
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")
    evi = image.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR": image.select("B8"),
            "RED": image.select("B4"),
            "BLUE": image.select("B2"),
        },
    ).rename("evi")
    return image.addBands([ndvi, ndbi, ndwi, evi])


def _reduce_collection(collection: ee.ImageCollection, method: str) -> ee.Image:
    """Applique la réduction temporelle (median ou mean)."""
    method = method.lower()
    if method == "mean":
        return collection.mean()
    return collection.median()


def get_s2_composite(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Produit un composite Sentinel-2 avec indices spectraux, reprojeté à 1 km.

    Pipeline :
      1. Filtrage spatial / temporel / nuages
      2. Masque QA60 (optionnel)
      3. Réduction temporelle (médiane par défaut)
      4. Conversion DN → réflectance (/10000)
      5. Calcul des indices
      6. Reprojection EPSG:32633 @ export_scale

    Returns
    -------
    ee.Image
        Bandes : ndvi, ndbi, ndwi, evi
    """
    cfg = config["sentinel2"]
    collection = get_s2_collection(aoi, config)

    composite = _reduce_collection(collection, cfg.get("composite_method", "median"))
    reflectance = composite.divide(cfg.get("scale_factor", 10000))
    indexed = add_spectral_indices(reflectance)
    output = indexed.select(S2_FEATURE_BANDS + S2_QA_BANDS)

    return reproject_to_target(output, config)