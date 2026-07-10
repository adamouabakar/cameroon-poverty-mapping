#!/usr/bin/env python
"""
Finalise le ré-export VIIRS : mosaïque + inférence + priorisation.

À lancer après téléchargement forcé des tuiles (--force).

Usage :
  python scripts/finalize_viirs_reexport.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
REPORT = PROJECT_ROOT / "outputs/reports/viirs_reexport_final.json"


def _run(script: str, *args: str) -> int:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n▶ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def main() -> int:
    steps = [
        ("download_gee_raster_local.py", "--mode", "national", "--mosaic-only"),
        ("run_national_inference.py", "--mode", "raster",
         "--features", "data/processed/rasters/cm_features_1km_v3.tif"),
        ("run_prioritization_maps.py",),
        ("run_national_uncertainty.py",),
    ]
    for step in steps:
        if _run(*step) != 0:
            return 1

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "viirs_collection": "NASA/VIIRS/002/VNP46A2",
        "complete": True,
        "mosaic": str(PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"),
        "wealth_map": str(PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model.tif"),
        "priority_map": str(PROJECT_ROOT / "outputs/maps/priority_index_1km.tif"),
        "uncertainty_map": str(PROJECT_ROOT / "outputs/maps/wealth_uncertainty_1km_model.tif"),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n✅ Ré-export VIIRS finalisé — {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())