#!/usr/bin/env python
"""
Ré-entraînement et évaluation LightGBM feature set v4 (GEE v3 + INS).

Produit :
  - outputs/reports/model_v4_results.json
  - notebooks/02_modeling_v4_executed.ipynb
  - models/wealth_model_lgbm_v0_gee_v4.pkl
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import pandas as pd

from run_notebook_02_pipeline import (  # noqa: E402
    FEATURE_COLUMNS_BY_SET,
    INS_FEATURE_COLS,
    run_notebook,
    run_pipeline,
)

V3_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_real.parquet"
V4_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_ins_v4.parquet"
V3_RESULTS = PROJECT_ROOT / "outputs/reports/real_model_results.json"
OUTPUT_JSON = PROJECT_ROOT / "outputs/reports/model_v4_results.json"


def _load_v3_baseline() -> dict:
    if V3_RESULTS.exists():
        data = json.loads(V3_RESULTS.read_text(encoding="utf-8"))
        return {
            "metrics_oof": data["metrics_oof"],
            "importance_gain": {
                row["feature"]: row["gain"] for row in data.get("top10_importance", [])
            },
            "source": "real_model_results.json",
        }
    return run_pipeline(feature_set="v3", use_fake=False, gee_parquet=V3_PARQUET, save_artifacts=False)


def _importance_table(importance: dict, features: list[str] | None = None) -> list[dict]:
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    if features:
        ranked = [(f, importance.get(f, 0.0)) for f in features]
    return [
        {"rank": i, "feature": f, "gain": round(float(g), 4)}
        for i, (f, g) in enumerate(ranked, 1)
    ]


def _delta_metrics(v3: dict, v4: dict) -> dict:
    keys = ("r2", "rmse", "mae", "spearman")
    return {k: round(v4[k] - v3[k], 6) for k in keys}


def _regional_oof_errors(feature_set: str, gee_parquet: Path) -> pd.DataFrame:
    from src.data.load_training_data import build_training_matrix, load_prepared_clusters
    from src.data.merge_features import merge_dhs_with_features
    from src.features.load_features import load_cluster_features
    from src.models.cv_pipeline import run_spatial_cv
    from src.models.evaluate import compute_metrics
    from src.utils.config import load_config
    from src.utils.spatial_cv import select_cv_strategy

    config = load_config(PROJECT_ROOT / "configs/default.yaml")
    config["features"]["feature_set"] = feature_set
    config["features"]["columns"] = FEATURE_COLUMNS_BY_SET[feature_set]
    config["features"]["fake"] = False
    config["features"]["source"] = "gee"
    config["features"]["gee_parquet"] = str(gee_parquet.relative_to(PROJECT_ROOT))

    gdf = load_prepared_clusters(PROJECT_ROOT / config["data"]["prepared_clusters"])
    features_df, _ = load_cluster_features(gdf, config, project_root=PROJECT_ROOT)
    training_df = merge_dhs_with_features(gdf, features_df)
    feature_cols = config["features"]["columns"]
    X, y, _meta = build_training_matrix(training_df, feature_cols=feature_cols)
    cv_strategy, _, _ = select_cv_strategy(
        gdf,
        preferred=config["model"]["cv_strategy"],
        n_folds=config["model"]["n_folds"],
        random_state=config["model"]["random_state"],
    )
    cv_results = run_spatial_cv(X, y, gdf, config, cv_strategy=cv_strategy, return_models=False)

    training_df = training_df.copy()
    training_df["y_pred"] = cv_results.oof_predictions.values
    training_df["residual"] = training_df["wealth_index"] - training_df["y_pred"]
    df = training_df[["cluster_id", "region", "wealth_index", "y_pred", "residual"]].rename(
        columns={"wealth_index": "y_true"}
    )
    agg = (
        df.groupby("region", as_index=False)
        .agg(
            n_clusters=("cluster_id", "count"),
            rmse=("residual", lambda s: float((s ** 2).mean() ** 0.5)),
            mae_residual=("residual", lambda s: float(s.abs().mean())),
            mean_residual=("residual", "mean"),
        )
    )
    agg["feature_set"] = feature_set
    return agg


def _plot_comparison(v3_m: dict, v4_m: dict, out_path: Path) -> None:
    metrics = ["r2", "spearman"]
    v3_vals = [v3_m[k] for k in metrics]
    v4_vals = [v4_m[k] for k in metrics]
    x = range(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([i - width / 2 for i in x], v3_vals, width, label="v3")
    ax.bar([i + width / 2 for i in x], v4_vals, width, label="v4")
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics)
    ax.set_title("Comparaison métriques OOF v3 vs v4")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Évaluation modèle v4 + comparaison v3")
    p.add_argument("--skip-notebook", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/prepare_final_features_v4.py")],
        cwd=PROJECT_ROOT,
    )

    print("📊 Baseline v3...")
    v3 = _load_v3_baseline()
    v3_metrics = v3["metrics_oof"]

    print("📊 Entraînement v4 (GEE v3 + INS)...")
    v4 = run_pipeline(
        feature_set="v4",
        use_fake=False,
        gee_parquet=V4_PARQUET,
        save_artifacts=True,
    )
    v4_metrics = v4["metrics_oof"]

    regional_v3 = _regional_oof_errors("v3", V3_PARQUET)
    regional_v4 = _regional_oof_errors("v4", V4_PARQUET)
    regional_compare = regional_v3.merge(
        regional_v4,
        on="region",
        suffixes=("_v3", "_v4"),
    )

    ins_importance = _importance_table(v4["importance_gain"], INS_FEATURE_COLS)
    delta = _delta_metrics(v3_metrics, v4_metrics)

    comp_plot = PROJECT_ROOT / "outputs/reports/v3_vs_v4_metrics.png"
    comp_plot.parent.mkdir(parents=True, exist_ok=True)
    _plot_comparison(v3_metrics, v4_metrics, comp_plot)

    regional_path = PROJECT_ROOT / "outputs/reports/regional_errors_v3_vs_v4.csv"
    regional_compare.to_csv(regional_path, index=False)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_set": "v4",
        "data_source": "real_dhs_2018 + gee_v3 + ins_ecam4",
        "n_clusters": v4["n_clusters"],
        "cv_strategy": v4["cv_strategy"],
        "n_features": len(FEATURE_COLUMNS_BY_SET["v4"]),
        "ins_source": {
            "survey": "ECAM 4",
            "producer": "INS Cameroun",
            "year": 2014,
        },
        "metrics_v4_oof": {k: round(v, 6) if isinstance(v, float) else v for k, v in v4_metrics.items()},
        "metrics_v3_oof": {k: round(v, 6) if isinstance(v, float) else v for k, v in v3_metrics.items()},
        "comparison_v3_vs_v4": {
            "metrics": {
                "v3": v3_metrics,
                "v4": v4_metrics,
                "delta_v4_minus_v3": delta,
            },
            "interpretation": {
                "r2": "Gain attendu si INS apporte signal régional non capturé par satellite.",
                "leakage_warning": (
                    "Variables INS constantes par région — risque de sur-apprentissage "
                    "régional et inflation OOF si plis CV mélangent mal les régions."
                ),
            },
        },
        "ins_feature_importance": ins_importance,
        "top10_importance_v4": _importance_table(v4["importance_gain"])[:10],
        "regional_errors": regional_compare.to_dict(orient="records"),
        "limitations": [
            "INS = agrégats régionaux (4 variables) — pas de résolution infra-régionale.",
            "ECAM 4 (2014) vs DHS 2018 — décalage temporel.",
            "Amélioration OOF peut refléter redondance avec signal déjà dans GEE (nuit, routes).",
            "Raster national v4 non disponible sans zonal stats admin1.",
        ],
        "artifacts": {
            "final_features": "data/processed/final_features_v4.parquet",
            "features_parquet": str(V4_PARQUET.relative_to(PROJECT_ROOT)),
            "model": "models/wealth_model_lgbm_v0_gee_v4.pkl",
            "comparison_plot": str(comp_plot.relative_to(PROJECT_ROOT)),
            "regional_errors_csv": str(regional_path.relative_to(PROJECT_ROOT)),
        },
        "phase3_recommendations": [
            "Évaluer v4 en region-based CV hold-out pour tester généralisation géographique.",
            "Cartographie nationale : ré-entraîner z-score v4 + inférence raster si admin1 rasterisé.",
            "Partenariat INS pour micro-données et ECAM 5 (2022).",
        ],
    }

    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.skip_notebook:
        subprocess.check_call(
            [sys.executable, str(PROJECT_ROOT / "scripts/build_notebook_02_v4.py")],
            cwd=PROJECT_ROOT,
        )
        run_notebook(
            feature_set="v4",
            use_fake=False,
            gee_parquet=V4_PARQUET,
            notebook_path=PROJECT_ROOT / "notebooks/02_modeling_v4.ipynb",
            output_path=PROJECT_ROOT / "notebooks/02_modeling_v4_executed.ipynb",
            timeout=1200,
        )

    print("\n" + "=" * 70)
    print("MODÉLISATION v4 — RÉSULTATS")
    print("=" * 70)
    print(f"R² v3 → v4     : {v3_metrics['r2']:.4f} → {v4_metrics['r2']:.4f} ({delta['r2']:+.4f})")
    print(f"Spearman v3→v4 : {v3_metrics['spearman']:.4f} → {v4_metrics['spearman']:.4f} ({delta['spearman']:+.4f})")
    print(f"RMSE v3→v4     : {v3_metrics['rmse']:.0f} → {v4_metrics['rmse']:.0f} ({delta['rmse']:+.0f})")
    print(f"Rapport        : {OUTPUT_JSON}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())