"""Export national vers Assets ou Google Drive."""

from __future__ import annotations

import ee

from src.features.gee.aoi import get_cameroon_geometry


def export_to_asset(
    image: ee.Image,
    asset_id: str,
    config: dict,
    aoi: ee.Geometry | None = None,
) -> ee.batch.Task:
    """Exporte l'image multi-bandes vers un Asset Earth Engine."""
    region = aoi or get_cameroon_geometry(config)
    export_bands = list(config["band_names"].values())
    export_image = image.select(export_bands).clip(region)

    task = ee.batch.Export.image.toAsset(
        image=export_image,
        description=asset_id.split("/")[-1],
        assetId=asset_id,
        region=region,
        scale=config["export_scale"],
        crs=config["crs"],
        maxPixels=config.get("max_pixels", int(1e9)),
        pyramidingPolicy={".default": "mean"},
    )
    task.start()
    return task


def export_to_drive(
    image: ee.Image,
    description: str,
    config: dict,
    aoi: ee.Geometry | None = None,
) -> ee.batch.Task:
    """Exporte vers Google Drive (fallback)."""
    region = aoi or get_cameroon_geometry(config)
    export_bands = list(config["band_names"].values())
    export_image = image.select(export_bands).clip(region)

    task = ee.batch.Export.image.toDrive(
        image=export_image,
        description=description,
        folder=config["export"]["drive_folder"],
        region=region,
        scale=config["export_scale"],
        crs=config["crs"],
        maxPixels=config.get("max_pixels", int(1e9)),
        fileFormat="GeoTIFF",
    )
    task.start()
    return task


def launch_national_export(
    image: ee.Image,
    config: dict,
    destination: str = "asset",
) -> ee.batch.Task:
    """
    Lance l'export national. Pour les très grands AOIs, préférer un découpage
    manuel par tuiles régionales (voir documentation/gee_features.md).
    """
    prefix = config["export"]["asset_prefix"]
    if destination == "asset":
        return export_to_asset(image, f"{prefix}/cm_features_1km_v1", config)
    if destination == "drive":
        return export_to_drive(image, "cm_features_1km_v1", config)
    raise ValueError(f"Destination inconnue : {destination}")