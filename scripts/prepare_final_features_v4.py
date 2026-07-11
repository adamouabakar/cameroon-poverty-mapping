#!/usr/bin/env python
"""
Prépare data/processed/final_features_v4.parquet (DHS + GEE v3 + INS).

Usage :
  python scripts/prepare_final_features_v4.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import pandas as pd

from src.ins.regions import INS_FEATURE_COLUMNS_V4

FINAL_OUTPUT = "data/processed/final_features_v4.parquet"
FEATURES_V4 = "data/processed/features/cluster_features_gee_ins_v4.parquet"
CLUSTERS = "data/processed/dhs_clusters_real.parquet"

V3_COLS = [
    "night_lights_mean", "ndvi_mean", "ndbi_mean",
    "dist_road_km", "dist_school_km", "dist_health_km",
    "pop_density", "elevation_m", "slope_deg", "ghsl_built_fraction",
    "precip_annual_mm", "precip_wet_season_mm", "precip_cv",
]
FEATURE_COLS_V4 = V3_COLS + INS_FEATURE_COLUMNS_V4


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Préparer final_features_v4.parquet")
    p.add_argument("--output", default=FINAL_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    v4_features = PROJECT_ROOT / FEATURES_V4
    if not v4_features.exists():
        subprocess.check_call(
            [sys.executable, str(PROJECT_ROOT / "scripts/merge_ins_features_v4.py")],
            cwd=PROJECT_ROOT,
        )

    clusters = gpd.read_parquet(PROJECT_ROOT / CLUSTERS)
    features = pd.read_parquet(v4_features)

    base = clusters.drop(columns=["geometry"], errors="ignore").merge(
        features.drop(columns=["region"], errors="ignore"),
        on="cluster_id",
        how="inner",
        validate="one_to_one",
    )

    if "region" not in base.columns:
        base["region"] = clusters.drop(columns=["geometry"]).set_index("cluster_id").loc[
            base["cluster_id"], "region"
        ].values

    feature_cols = FEATURE_COLS_V4
    keep = ["cluster_id", "latitude", "longitude", "urban_rural", "region", "wealth_index"]
    keep += [c for c in feature_cols if c in base.columns]
    keep = list(dict.fromkeys(keep))
    final = base[keep].copy()

    missing = final[feature_cols].isna().any().any()
    if missing:
        raise ValueError("Valeurs manquantes dans final_features_v4")

    out = PROJECT_ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    final.to_parquet(out, index=False)

    print("✅ final_features_v4.parquet prêt")
    print(f"  Lignes    : {len(final)}")
    print(f"  Features  : {len(feature_cols)}")
    print(f"  Sortie    : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())