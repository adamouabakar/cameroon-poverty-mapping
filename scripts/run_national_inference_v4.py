#!/usr/bin/env python
"""
Inférence nationale modèle v4 (GEE v3 + INS ECAM 4) sur grille ~1 km.

Usage :
  python scripts/run_national_inference_v4.py
  python scripts/run_national_inference_v4.py --features data/processed/rasters/cm_features_1km_v3.tif
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

FEATURES_DEFAULT = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
MODEL_V4 = PROJECT_ROOT / "models/wealth_model_lgbm_v0_gee_v4.pkl"
CLUSTERS = PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet"
INS_PARQUET = PROJECT_ROOT / "data/processed/ins_contextual_data.parquet"
OUT_TIF = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model_v4.tif"
OUT_PNG = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model_v4.png"
REPORT = PROJECT_ROOT / "outputs/reports/national_inference_v4.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inférence nationale wealth v4")
    p.add_argument("--features", default=str(FEATURES_DEFAULT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    features_path = PROJECT_ROOT / args.features

    for path, label in [
        (features_path, "features raster"),
        (MODEL_V4, "model v4"),
        (CLUSTERS, "clusters"),
        (INS_PARQUET, "INS contextual"),
    ]:
        if not path.exists():
            print(f"❌ {label} introuvable : {path}")
            return 1

    from src.features.gee.config import load_gee_config, resolve_feature_set
    from src.models.predict_raster import predict_wealth_raster_v4
    from src.visualization.static_maps import plot_raster_preview

    gee_config = resolve_feature_set({**load_gee_config(), "feature_set": "v3"})

    print("▶ Inférence raster v4 (GEE + INS régional)…")
    predict_wealth_raster_v4(
        features_path,
        MODEL_V4,
        OUT_TIF,
        gee_config,
        clusters_path=CLUSTERS,
        ins_parquet_path=INS_PARQUET,
    )

    plot_raster_preview(
        OUT_TIF,
        OUT_PNG,
        title="Cameroun — wealth index estimé (modèle v4, grille 1 km)",
        colorbar_label="Wealth index DHS (hv271)",
    )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": str(MODEL_V4),
        "feature_set": "v4",
        "features_raster": str(features_path),
        "wealth_raster": str(OUT_TIF),
        "preview": str(OUT_PNG),
        "ins_assignment": "nearest_dhs_cluster_region",
        "note": (
            "Variables INS constantes par région DHS — assignation par grappe la plus proche. "
            "Carte exploratoire, pas micro-résolution INS."
        ),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Inférence nationale v4 terminée")
    print(f"   GeoTIFF : {OUT_TIF}")
    print(f"   Aperçu  : {OUT_PNG}")
    print(f"   Rapport : {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())