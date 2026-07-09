#!/usr/bin/env python
"""Affiche la progression du téléchargement national par tuiles."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TILES_DIR = PROJECT_ROOT / "data/processed/rasters/tiles"
MOSAIC = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
TEST = PROJECT_ROOT / "data/processed/rasters/cm_features_test_1km_v3.tif"

tiles = sorted(TILES_DIR.glob("tile_*.tif")) if TILES_DIR.exists() else []
expected = 96  # grille 1° sur bbox Cameroun (8° lon × 12° lat)
pct = min(100, int(100 * len(tiles) / expected)) if expected else 0
print(f"Tuiles téléchargées : {len(tiles)} / ~{expected} ({pct}%)")
if tiles:
    total_mb = sum(t.stat().st_size for t in tiles) / 1e6
    print(f"Volume tuiles     : {total_mb:.1f} MB")
print(f"Mosaïque nationale: {'✅' if MOSAIC.exists() else '⏳'} {MOSAIC}")
print(f"Raster test       : {'✅' if TEST.exists() else '❌'} {TEST}")