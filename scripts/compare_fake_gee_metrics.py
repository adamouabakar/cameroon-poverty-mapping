#!/usr/bin/env python
"""Compare métriques OOF fake vs GEE."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load_training_data import load_prepared_clusters
from src.features.load_features import load_cluster_features, resolve_feature_source
from src.utils.config import load_config


def main() -> None:
    fake = json.loads((PROJECT_ROOT / "outputs/reports/cv_metrics_fake.json").read_text())
    gee = json.loads((PROJECT_ROOT / "outputs/reports/cv_metrics_gee.json").read_text())
    imp_fake = pd.read_csv(PROJECT_ROOT / "outputs/reports/feature_importance_gain_fake.csv")
    imp_gee = pd.read_csv(PROJECT_ROOT / "outputs/reports/feature_importance_gain_gee.csv")

    cfg = load_config()
    gdf = load_prepared_clusters(PROJECT_ROOT / cfg["data"]["prepared_clusters"])
    print("=== load_cluster_features ===")
    print("resolve_feature_source:", resolve_feature_source(cfg))
    df, src = load_cluster_features(gdf, cfg)
    print(f"loaded {len(df)} rows | source={src}")

    print("\n=== OOF METRICS fake vs GEE ===")
    for k in ["r2", "rmse", "mae", "spearman"]:
        fv = fake["global_oof_metrics"][k]
        gv = gee["global_oof_metrics"][k]
        print(f"{k:10s}  fake={fv:7.3f}  gee={gv:7.3f}")

    print("\n=== FEATURE IMPORTANCE (gain) ===")
    merged = imp_fake.merge(imp_gee, on="feature", suffixes=("_fake", "_gee"))
    print(merged.sort_values("gain_gee", ascending=False).to_string(index=False))

    feat = pd.read_parquet(PROJECT_ROOT / "data/processed/features/cluster_features_gee.parquet")
    training = pd.read_parquet(PROJECT_ROOT / "data/processed/training/training_matrix.parquet")
    corr = training[cfg["features"]["columns"]].corrwith(training["wealth_index"]).abs()

    print("\n=== FEATURES PROBLÉMATIQUES (GEE) ===")
    for col in ["dist_school_km", "dist_health_km", "built_density"]:
        s = feat[col]
        print(
            f"{col}: nunique={s.nunique()} | min={s.min():.3f} max={s.max():.3f} "
            f"std={s.std():.3f} | |corr|={corr[col]:.3f} | gain={merged.loc[merged.feature==col,'gain_gee'].iloc[0]:.2f}"
        )


if __name__ == "__main__":
    main()