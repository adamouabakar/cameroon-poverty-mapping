#!/usr/bin/env python
"""
Finalise la couverture nationale 100 % :
  1. Télécharge les tuiles manquantes (reprise automatique)
  2. Reconstruit la mosaïque
  3. Lance l'inférence raster nationale

Usage :
  python scripts/finalize_national_coverage.py
  python scripts/finalize_national_coverage.py --download-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
TILES_DIR = PROJECT_ROOT / "data/processed/rasters/tiles"
MOSAIC = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
REPORT = PROJECT_ROOT / "outputs/reports/national_coverage_final.json"
LOCK = PROJECT_ROOT / "data/processed/rasters/.download.lock"


def _expected_tiles() -> int:
    # Grille 1° sur bbox Cameroun (8° lon × 12° lat) — pas de dépendance GEE locale.
    return 96


def _run(script: str, *args: str) -> int:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n▶ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def _tile_count(expected: int) -> tuple[int, int]:
    tiles = list(TILES_DIR.glob("tile_*.tif")) if TILES_DIR.exists() else []
    valid = [t for t in tiles if t.stat().st_size > 1000]
    return len(valid), expected


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Finaliser couverture nationale 100%")
    p.add_argument("--download-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    expected = _expected_tiles()
    n, _ = _tile_count(expected)
    print(f"Tuiles actuelles : {n}/{expected}")

    if LOCK.exists():
        print(f"⚠️  Téléchargement en cours (lock: {LOCK}) — attendez la fin.")
        return 1

    if n < expected:
        code = _run("download_gee_raster_local.py", "--mode", "national", "--tiles")
        n, _ = _tile_count(expected)
        print(f"Tuiles après téléchargement : {n}/{expected}")
        if n < expected:
            print("⏳ Reprise nécessaire — relancez finalize_national_coverage.py")
            return 2 if not args.download_only else 0

    if args.download_only:
        return 0

    code = _run("download_gee_raster_local.py", "--mode", "national", "--mosaic-only")
    if code != 0:
        return code

    code = _run(
        "run_national_inference.py",
        "--mode", "raster",
        "--features", "data/processed/rasters/cm_features_1km_v3.tif",
    )
    if code != 0:
        return code

    n, expected = _tile_count(expected)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tiles": n,
        "expected": expected,
        "complete": n >= expected,
        "mosaic": str(MOSAIC),
        "wealth_map": str(PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model.tif"),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n✅ Couverture nationale finalisée — {n}/{expected} tuiles")
    print(f"   Rapport : {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())