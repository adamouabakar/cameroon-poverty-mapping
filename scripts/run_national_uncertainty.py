#!/usr/bin/env python
"""
Carte d'incertitude nationale alignée sur le raster wealth (mode GEE direct).

Usage :
  python scripts/run_national_uncertainty.py
  python scripts/run_national_uncertainty.py --wealth outputs/maps/wealth_index_predicted_1km_model.tif
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

WEALTH_DEFAULT = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model.tif"
CLUSTERS = PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet"
OOF = PROJECT_ROOT / "data/processed/training/oof_predictions.parquet"
OUT_TIF = PROJECT_ROOT / "outputs/maps/wealth_uncertainty_1km_model.tif"
OUT_PNG = PROJECT_ROOT / "outputs/maps/wealth_uncertainty_1km_model.png"
REPORT = PROJECT_ROOT / "outputs/reports/national_uncertainty.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Incertitude nationale raster direct")
    p.add_argument("--wealth", default=str(WEALTH_DEFAULT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    wealth_path = PROJECT_ROOT / args.wealth
    for path, label in [(wealth_path, "wealth raster"), (CLUSTERS, "clusters"), (OOF, "oof")]:
        if not path.exists():
            print(f"❌ {label} introuvable : {path}")
            return 1

    import geopandas as gpd
    import pandas as pd

    from src.models.uncertainty_raster import export_uncertainty_on_wealth_grid
    from src.visualization.static_maps import plot_raster_preview

    clusters = gpd.read_parquet(CLUSTERS)
    oof = pd.read_parquet(OOF)

    print("▶ Export incertitude sur grille wealth…")
    export_uncertainty_on_wealth_grid(wealth_path, clusters, oof, OUT_TIF)

    plot_raster_preview(
        OUT_TIF,
        OUT_PNG,
        title="Incertitude OOF interpolée — grille modèle 1 km",
        cmap="Purples",
    )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "method": "oof_half_width_rbf_on_wealth_grid",
        "wealth_raster": str(wealth_path),
        "uncertainty_raster": str(OUT_TIF),
        "preview": str(OUT_PNG),
        "n_clusters": len(clusters),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"✅ Incertitude nationale : {OUT_TIF}")
    print(f"   Aperçu : {OUT_PNG}")
    print(f"   Rapport : {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())