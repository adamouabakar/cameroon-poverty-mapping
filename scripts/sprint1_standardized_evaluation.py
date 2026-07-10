#!/usr/bin/env python
"""
Sprint 1 — Évaluation avec wealth_index standardisé (z-score).

Produit :
  - data/processed/training/wealth_scaler.json
  - models/wealth_scaler_v3.json
  - outputs/reports/real_model_results_zscore.json
  - models/wealth_model_lgbm_v0_gee_v3_zscore.pkl
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.data.load_training_data import build_training_matrix, load_prepared_clusters
from src.data.merge_features import merge_dhs_with_features
from src.data.wealth_scaling import WealthScaler, save_scaler
from src.features.load_features import load_cluster_features
from src.models.cv_pipeline import run_spatial_cv
from src.models.evaluate import compute_metrics, compute_spearman
from src.models.save_load import save_model
from src.models.train import extract_median_best_iteration, train_final_model
from src.utils.config import load_config
from src.utils.spatial_cv import select_cv_strategy

FEATURE_COLS = [
    "night_lights_mean", "ndvi_mean", "ndbi_mean",
    "dist_road_km", "dist_school_km", "dist_health_km",
    "pop_density", "elevation_m", "slope_deg", "ghsl_built_fraction",
    "precip_annual_mm", "precip_wet_season_mm", "precip_cv",
]


def main() -> int:
    config = load_config(PROJECT_ROOT / "configs/default.yaml")
    config["features"]["feature_set"] = "v3"
    config["features"]["columns"] = FEATURE_COLS
    config["features"]["fake"] = False
    config["features"]["source"] = "gee"
    config["features"]["gee_parquet"] = "data/processed/features/cluster_features_gee_real.parquet"

    gdf = load_prepared_clusters(PROJECT_ROOT / config["data"]["prepared_clusters"])
    features_df, _ = load_cluster_features(gdf, config, project_root=PROJECT_ROOT)
    training_df = merge_dhs_with_features(gdf, features_df)

    scaler = WealthScaler(mean=0.0, std=1.0).fit(training_df["wealth_index"])
    scaler_path = PROJECT_ROOT / "data/processed/training/wealth_scaler.json"
    scaler_versioned = PROJECT_ROOT / "models/wealth_scaler_v3.json"
    save_scaler(scaler, scaler_path)
    save_scaler(scaler, scaler_versioned)

    training_df = training_df.copy()
    training_df["wealth_index_z"] = scaler.transform(training_df["wealth_index"])

    X, y_raw, meta = build_training_matrix(training_df, feature_cols=FEATURE_COLS)
    y = pd.Series(scaler.transform(y_raw), index=y_raw.index, name="wealth_index_z")

    cv_strategy, fold_ids, balance_report = select_cv_strategy(
        gdf,
        preferred=config["model"]["cv_strategy"],
        n_folds=config["model"]["n_folds"],
        random_state=config["model"]["random_state"],
    )

    cv_results = run_spatial_cv(X, y, gdf, config, cv_strategy=cv_strategy, return_models=True)

    metrics_z = compute_metrics(y, cv_results.oof_predictions)
    metrics_z["spearman"] = compute_spearman(y, cv_results.oof_predictions)

    oof_raw = scaler.inverse_transform(cv_results.oof_predictions)
    metrics_raw = compute_metrics(y_raw, oof_raw)
    metrics_raw["spearman"] = compute_spearman(y_raw, oof_raw)

    median_iter = extract_median_best_iteration(cv_results)
    final_model = train_final_model(
        X, y, config, median_best_iteration=median_iter, strata=meta["urban_rural"]
    )
    model_path = PROJECT_ROOT / "models/wealth_model_lgbm_v0_gee_v3_zscore.pkl"
    save_model(final_model, model_path)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": "1",
        "feature_set": "v3",
        "n_clusters": len(gdf),
        "cv_strategy": cv_strategy,
        "wealth_scaler": scaler.to_dict(),
        "metrics_oof_zscore": metrics_z,
        "metrics_oof_raw_hv271": metrics_raw,
        "interpretation": {
            "rmse_zscore": "RMSE en écarts-types DHS — comparable entre pays/versions",
            "rmse_raw": "RMSE en unités hv271 brutes (héritage Phase 1)",
        },
        "balance_report": balance_report,
        "artifacts": {
            "scaler": str(scaler_path),
            "scaler_versioned": str(scaler_versioned),
            "model_zscore": str(model_path),
        },
    }

    out_path = PROJECT_ROOT / "outputs/reports/real_model_results_zscore.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("✅ Évaluation z-score terminée")
    print(f"  Scaler       : {scaler_path}")
    print(f"  Scaler (git) : {scaler_versioned}")
    print(f"  Modèle       : {model_path}")
    print(f"  R² (z)       : {metrics_z['r2']:.4f}")
    print(f"  RMSE (z)     : {metrics_z['rmse']:.4f} σ")
    print(f"  Spearman     : {metrics_z['spearman']:.4f}")
    print(f"  R² (raw)     : {metrics_raw['r2']:.4f}")
    print(f"  RMSE (raw)   : {metrics_raw['rmse']:.0f}")
    print(f"  Rapport      : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())