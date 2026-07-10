#!/usr/bin/env python
"""
Télécharge localement un raster features GEE v3 via getDownloadURL.

Contourne le téléchargement manuel Google Drive pour Sprint 1.

Usage :
  python scripts/download_gee_raster_local.py --mode test
  python scripts/download_gee_raster_local.py --mode national --tiles
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import ee
import rasterio
from rasterio.merge import merge as rio_merge

from src.features.gee.aoi import get_aoi_geometry, get_cameroon_geometry
from src.features.gee.client import initialize_gee
from src.features.gee.config import load_gee_config, resolve_feature_set
from src.features.gee.stack import build_feature_image, get_model_bands

RASTERS_DIR = PROJECT_ROOT / "data/processed/rasters"
TILES_DIR = RASTERS_DIR / "tiles"
LOCK_FILE = RASTERS_DIR / ".download.lock"


def _download_url(image: ee.Image, region: ee.Geometry, config: dict) -> str:
    bands = get_model_bands(config)
    export_image = image.select(bands).clip(region).toFloat()
    params = {
        "scale": config["export_scale"],
        "crs": config["crs"],
        "region": region,
        "format": "GEO_TIFF",
        "filePerBand": False,
    }
    return export_image.getDownloadURL(params)


def _fetch_geotiff(url: str, dest: Path, retries: int = 5) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            print(f"   Téléchargement (tentative {attempt}/{retries})…")
            urllib.request.urlretrieve(url, dest)
            return
        except Exception as exc:
            last_err = exc
            time.sleep(min(30, 5 * attempt))
    raise RuntimeError(f"Échec téléchargement {dest}: {last_err}") from last_err


def _tag_band_descriptions(path: Path, band_names: list[str]) -> None:
    """Assure que les bandes ont des descriptions pour predict_raster."""
    with rasterio.open(path, "r+") as ds:
        count = min(ds.count, len(band_names))
        for i in range(count):
            ds.set_band_description(i + 1, band_names[i])


def download_region(
    image: ee.Image,
    region: ee.Geometry,
    config: dict,
    dest: Path,
) -> Path:
    url = _download_url(image, region, config)
    _fetch_geotiff(url, dest)
    _tag_band_descriptions(dest, get_model_bands(config))
    return dest


def _bounds_from_geometry(geom_info: dict) -> tuple[float, float, float, float]:
    """Extrait west/south/east/north depuis getInfo() d'une géométrie EE."""
    if "coordinates" not in geom_info:
        raise ValueError(f"Géométrie non supportée : {geom_info.get('type')}")
    if geom_info["type"] == "Polygon":
        ring = geom_info["coordinates"][0]
    elif geom_info["type"] == "MultiPolygon":
        ring = geom_info["coordinates"][0][0]
    else:
        raise ValueError(f"Type géométrique non supporté : {geom_info['type']}")
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return min(lons), min(lats), max(lons), max(lats)


def _tile_rectangles(config: dict) -> list[ee.Geometry]:
    cm = get_cameroon_geometry(config)
    step = float(config.get("export", {}).get("national_tile_degrees", 1.0))
    west, south, east, north = _bounds_from_geometry(cm.bounds().getInfo())

    rects = []
    lat = south
    while lat < north:
        lon = west
        while lon < east:
            rects.append(ee.Geometry.Rectangle([lon, lat, min(lon + step, east), min(lat + step, north)]))
            lon += step
        lat += step
    return rects


def download_test(config: dict) -> Path:
    aoi = get_aoi_geometry(config, mode="test")
    image = build_feature_image(aoi, config)
    dest = RASTERS_DIR / "cm_features_test_1km_v3.tif"
    print(f"▶ Export local test AOI → {dest}")
    return download_region(image, aoi, config, dest)


def mosaic_existing_tiles(config: dict) -> Path:
    tile_paths = sorted(TILES_DIR.glob("tile_*.tif"))
    if not tile_paths:
        raise RuntimeError(f"Aucune tuile dans {TILES_DIR}")
    mosaic_path = RASTERS_DIR / "cm_features_1km_v3.tif"
    print(f"▶ Mosaïque {len(tile_paths)} tuiles existantes → {mosaic_path}", flush=True)
    datasets = [rasterio.open(p) for p in tile_paths]
    try:
        mosaic, out_transform = rio_merge(datasets)
        profile = datasets[0].profile.copy()
        profile.update(
            height=mosaic.shape[1],
            width=mosaic.shape[2],
            transform=out_transform,
            count=mosaic.shape[0],
        )
        mosaic_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(mosaic_path, "w", **profile) as dst:
            dst.write(mosaic)
        _tag_band_descriptions(mosaic_path, get_model_bands(config))
    finally:
        for ds in datasets:
            ds.close()
    return mosaic_path


def download_national_tiles(config: dict, *, force: bool = False) -> Path:
    image = build_feature_image(get_cameroon_geometry(config), config)
    tiles = _tile_rectangles(config)
    TILES_DIR.mkdir(parents=True, exist_ok=True)
    tile_paths: list[Path] = []

    print(f"▶ Export national par tuiles ({len(tiles)} rectangles 1°)", flush=True)
    for i, rect in enumerate(tiles):
        dest = TILES_DIR / f"tile_{i:03d}.tif"
        if not force and dest.exists() and dest.stat().st_size > 1000:
            print(f"   Tuile {i+1}/{len(tiles)} — déjà présente", flush=True)
            tile_paths.append(dest)
            continue
        print(f"   Tuile {i+1}/{len(tiles)} — téléchargement…", flush=True)
        try:
            download_region(image, rect, config, dest)
            tile_paths.append(dest)
        except Exception as exc:
            print(f"   ⚠️  Tuile {i} ignorée : {exc}")

    if not tile_paths:
        raise RuntimeError("Aucune tuile téléchargée.")

    if len(tile_paths) < len(tiles):
        print(
            f"⏳ {len(tile_paths)}/{len(tiles)} tuiles — mosaïque différée "
            f"(relancez ou utilisez finalize_national_coverage.py)",
            flush=True,
        )
        return TILES_DIR

    return mosaic_existing_tiles(config)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Téléchargement local raster GEE v3")
    p.add_argument("--mode", choices=["test", "national"], default="test")
    p.add_argument("--tiles", action="store_true", help="Découpage national en tuiles 1°")
    p.add_argument("--mosaic-only", action="store_true", help="Assembler les tuiles déjà téléchargées")
    p.add_argument("--force", action="store_true", help="Re-télécharger même si la tuile existe")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "national" and args.tiles and not args.mosaic_only:
        if LOCK_FILE.exists():
            print(f"⚠️  Téléchargement déjà en cours (lock: {LOCK_FILE})")
            return 1
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text("running", encoding="utf-8")

    config = resolve_feature_set({**load_gee_config(), "feature_set": "v3"})
    initialize_gee(project_id=config.get("project_id"))

    try:
        return _main_body(args, config)
    finally:
        if LOCK_FILE.exists() and args.mode == "national" and args.tiles and not args.mosaic_only:
            LOCK_FILE.unlink(missing_ok=True)


def _main_body(args: argparse.Namespace, config: dict) -> int:

    if args.mode == "test":
        dest = download_test(config)
    elif args.mosaic_only:
        dest = mosaic_existing_tiles(config)
    else:
        if not args.tiles:
            print("❌ Le mode national requiert --tiles (limite getDownloadURL GEE).")
            return 1
        dest = download_national_tiles(config, force=args.force)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "output": str(dest),
    }
    if dest.is_file():
        report["size_mb"] = round(dest.stat().st_size / 1e6, 2)
    report_path = PROJECT_ROOT / "outputs/reports/gee_local_download.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"✅ Terminé : {dest}")
    if dest.is_file():
        print(f"   Taille : {report['size_mb']} MB")
    print(f"   Rapport : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())