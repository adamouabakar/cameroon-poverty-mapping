"""Export national vers Assets ou Google Drive."""

from __future__ import annotations

import ee

from src.features.gee.aoi import get_cameroon_geometry


def ensure_asset_folder(asset_prefix: str) -> None:
    """Crée le dossier Asset parent s'il n'existe pas encore."""
    try:
        ee.data.getAsset(asset_prefix)
    except ee.EEException:
        ee.data.createAsset({"type": "Folder"}, asset_prefix)


def export_to_asset(
    image: ee.Image,
    asset_id: str,
    config: dict,
    aoi: ee.Geometry | None = None,
) -> ee.batch.Task:
    """Exporte l'image multi-bandes vers un Asset Earth Engine."""
    region = aoi or get_cameroon_geometry(config)
    export_bands = list(config["band_names"].values())
    export_image = image.select(export_bands).clip(region).toFloat()

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
    export_image = image.select(export_bands).clip(region).toFloat()

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


def _national_export_name(config: dict) -> str:
    return config.get("export", {}).get("national_asset_name", "cm_features_1km_v3")


def launch_national_export(
    image: ee.Image,
    config: dict,
    destination: str = "asset",
    *,
    aoi: ee.Geometry | None = None,
    description: str | None = None,
) -> ee.batch.Task:
    """
    Lance l'export national. Pour les très grands AOIs, préférer un découpage
    manuel par tuiles régionales (voir documentation/gee_features.md).
    """
    name = description or _national_export_name(config)
    prefix = config["export"]["asset_prefix"]
    if destination == "asset":
        ensure_asset_folder(prefix)
        return export_to_asset(image, f"{prefix}/{name}", config, aoi=aoi)
    if destination == "drive":
        return export_to_drive(image, name, config, aoi=aoi)
    raise ValueError(f"Destination inconnue : {destination}")