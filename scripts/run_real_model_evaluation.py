#!/usr/bin/env python
"""
Entraînement et évaluation LightGBM sur vraies grappes DHS 2018 + features GEE v3.

Produit :
  - outputs/reports/real_model_results.json
  - outputs/reports/feature_importance_gain_real.csv
  - outputs/reports/oof_scatter_real.png
  - outputs/reports/feature_importance_real.png
  - notebooks/02_modeling_real_data_executed.ipynb (via nbclient)

Usage :
  python scripts/run_real_model_evaluation.py
  python scripts/run_real_model_evaluation.py --skip-notebook
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from run_notebook_02_pipeline import (  # noqa: E402
    FEATURE_COLUMNS_BY_SET,
    run_notebook,
    run_pipeline,
)

REAL_CLUSTERS = "data/processed/dhs_clusters_real.parquet"
REAL_GEE = "data/processed/features/cluster_features_gee_real.parquet"
OUTPUT_JSON = "outputs/reports/real_model_results.json"
FAKE_V3_JSON = "outputs/reports/v2_vs_v3_comparison.json"

CHIRPS_COLS = ("precip_annual_mm", "precip_wet_season_mm", "precip_cv")
GHSL_COL = "ghsl_built_fraction"


def _importance_top10(importance: dict) -> list[dict]:
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    return [{"rank": i, "feature": f, "gain": round(g, 4)} for i, (f, g) in enumerate(ranked[:10], 1)]


def _importance_rank(importance: dict, feature: str) -> int | None:
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for i, (name, _) in enumerate(ranked, start=1):
        if name == feature:
            return i
    return None


def _data_quality_report(gdf, features_df, training_df) -> dict:
    return {
        "n_clusters_dhs": len(gdf),
        "n_clusters_features": len(features_df),
        "n_rows_merged": len(training_df),
        "merge_complete": len(training_df) == len(gdf),
        "missing_wealth_index": int(training_df["wealth_index"].isna().sum()),
        "wealth_index_stats": {
            "mean": float(training_df["wealth_index"].mean()),
            "std": float(training_df["wealth_index"].std()),
            "min": float(training_df["wealth_index"].min()),
            "median": float(training_df["wealth_index"].median()),
            "max": float(training_df["wealth_index"].max()),
        },
        "urban_rural_counts": training_df["urban_rural"].value_counts().to_dict(),
        "feature_missing_rates": {
            col: float(training_df[col].isna().mean())
            for col in FEATURE_COLUMNS_BY_SET["v3"]
            if col in training_df.columns
        },
    }


def _plot_oof_scatter(y, y_pred, metrics: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y, y_pred, alpha=0.5, s=30, edgecolors="none")
    lims = [
        min(y.min(), y_pred.min()),
        max(y.max(), y_pred.max()),
    ]
    ax.plot(lims, lims, "r--", lw=1, label="y = x")
    ax.set_xlabel("Wealth index observé (hv271, moyenne grappe)")
    ax.set_ylabel("Prédiction OOF")
    ax.set_title(
        f"OOF — R²={metrics['r2']:.3f}, Spearman={metrics['spearman']:.3f}, "
        f"RMSE={metrics['rmse']:.0f}"
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _plot_importance(importance: dict, out_path: Path, top_n: int = 13) -> None:
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
    features = [f for f, _ in ranked][::-1]
    gains = [g for _, g in ranked][::-1]
    colors = [
        "#2ecc71" if f in CHIRPS_COLS else "#3498db" if f == GHSL_COL else "#95a5a6"
        for f in features
    ]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(features, gains, color=colors)
    ax.set_xlabel("Gain LightGBM")
    ax.set_title("Feature importance — données réelles DHS 2018 (v3)")
    from matplotlib.patches import Patch
    ax.legend(
        handles=[
            Patch(color="#2ecc71", label="CHIRPS"),
            Patch(color="#3498db", label="GHSL"),
            Patch(color="#95a5a6", label="Autres"),
        ],
        loc="lower right",
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _load_fake_baseline() -> dict:
    path = PROJECT_ROOT / FAKE_V3_JSON
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    v3 = data.get("v3_detail", {})
    v2 = data.get("v2_detail", {})
    return {
        "fake_v3_metrics": v3.get("metrics_oof"),
        "fake_v2_metrics": v2.get("metrics_oof"),
        "fake_v3_importance": v3.get("importance_gain"),
        "fake_n_clusters": v3.get("n_clusters"),
        "source_file": str(path),
    }


def _build_comparison(real_v3: dict, real_v2: dict | None, fake: dict) -> dict:
    rv3 = real_v3["metrics_oof"]
    fv3 = fake.get("fake_v3_metrics") or {}
    delta_fake = {}
    if fv3:
        delta_fake = {
            "r2": round(rv3["r2"] - fv3.get("r2", 0), 4),
            "spearman": round(rv3["spearman"] - fv3.get("spearman", 0), 4),
            "rmse": round(rv3["rmse"] - fv3.get("rmse", 0), 4),
        }

    chirps_real = {
        c: {
            "gain": real_v3["importance_gain"].get(c, 0),
            "rank": _importance_rank(real_v3["importance_gain"], c),
        }
        for c in CHIRPS_COLS
    }
    ghsl_real = {
        "gain": real_v3["importance_gain"].get(GHSL_COL, 0),
        "rank": _importance_rank(real_v3["importance_gain"], GHSL_COL),
    }

    chirps_fake = {}
    if fake.get("fake_v3_importance"):
        imp = fake["fake_v3_importance"]
        chirps_fake = {c: {"gain": imp.get(c, 0)} for c in CHIRPS_COLS}

    v2v3_real = None
    if real_v2:
        m2 = real_v2["metrics_oof"]
        v2v3_real = {
            "delta_r2_v3_minus_v2": round(rv3["r2"] - m2["r2"], 4),
            "delta_spearman": round(rv3["spearman"] - m2["spearman"], 4),
            "delta_rmse": round(rv3["rmse"] - m2["rmse"], 4),
            "v2_metrics": m2,
            "v2_ghsl_importance": {
                "gain": real_v2["importance_gain"].get(GHSL_COL, 0),
                "rank": _importance_rank(real_v2["importance_gain"], GHSL_COL),
            },
        }

    return {
        "real_vs_fake_v3": {
            "fake_n_clusters": fake.get("fake_n_clusters"),
            "fake_metrics": fv3,
            "real_metrics": rv3,
            "delta_real_minus_fake": delta_fake,
        },
        "chirps_impact_real": chirps_real,
        "chirps_impact_fake": chirps_fake,
        "ghsl_impact_real": ghsl_real,
        "v2_vs_v3_real": v2v3_real,
    }


def _strengths_and_limits(real_v3: dict, comparison: dict) -> dict:
    m = real_v3["metrics_oof"]
    strengths = []
    limits = []
    improvements = []

    if m["r2"] > 0:
        strengths.append(f"R² OOF positif ({m['r2']:.3f}) — le modèle explique une part de la variance.")
    if m["spearman"] > 0.3:
        strengths.append(f"Corrélation de rang modérée à forte (Spearman={m['spearman']:.3f}).")

    chirps = comparison["chirps_impact_real"]
    if any(chirps[c]["gain"] > 0 for c in CHIRPS_COLS):
        strengths.append("Au moins une feature CHIRPS contribue au modèle (gain > 0).")

    if comparison["ghsl_impact_real"]["gain"] > 0:
        strengths.append(f"GHSL actif (gain={comparison['ghsl_impact_real']['gain']:.1f}, rang {comparison['ghsl_impact_real']['rank']}).")

    delta = comparison["real_vs_fake_v3"].get("delta_real_minus_fake", {})
    if delta.get("r2", 0) > 0.1:
        strengths.append("Performance nettement supérieure aux données fictives.")

    if m["r2"] < 0.3:
        limits.append("R² OOF modeste — variance résiduelle importante à 1 km.")
    if m["spearman"] < 0.4:
        limits.append("Spearman < 0.4 — ordre relatif des grappes imparfaitement capturé.")

    if comparison["ghsl_impact_real"]["gain"] == 0:
        limits.append("GHSL sans gain LightGBM sur données réelles.")

    limits.append("wealth_index (hv271) non standardisé — RMSE en unités DHS brutes.")
    limits.append("430 grappes — risque de sur-apprentissage malgré CV spatiale.")

    improvements.extend([
        "Standardiser wealth_index (z-score) pour stabiliser LightGBM.",
        "Tester v2 vs v3 systématiquement sur hold-out régional.",
        "Migrer VIIRS vers NASA/VIIRS/002.",
        "Enrichir avec Meta RWI ou données administratives (Phase 1 suite).",
        "Cartographier les prédictions OOF par région pour diagnostic spatial.",
    ])

    return {"strengths": strengths, "limits": limits, "improvement_paths": improvements}


def run_real_evaluation(skip_notebook: bool = False) -> dict:
    from src.data.load_training_data import load_prepared_clusters
    from src.data.merge_features import merge_dhs_with_features
    from src.features.load_features import load_cluster_features
    from src.utils.config import load_config

    reports_dir = PROJECT_ROOT / "outputs/reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(PROJECT_ROOT / "configs/default.yaml")
    config["data"]["prepared_clusters"] = REAL_CLUSTERS
    config["features"]["gee_parquet"] = REAL_GEE
    config["features"]["feature_set"] = "v3"
    config["features"]["columns"] = FEATURE_COLUMNS_BY_SET["v3"]
    config["features"]["fake"] = False
    config["features"]["source"] = "gee"

    gdf = load_prepared_clusters(PROJECT_ROOT / REAL_CLUSTERS)
    features_df, _ = load_cluster_features(gdf, config, project_root=PROJECT_ROOT)
    training_df = merge_dhs_with_features(gdf, features_df)
    data_qa = _data_quality_report(gdf, features_df, training_df)

    print("📊 Pipeline v3 — données réelles DHS 2018...")
    real_v3 = run_pipeline(
        feature_set="v3",
        use_fake=False,
        gee_parquet=PROJECT_ROOT / REAL_GEE,
        save_artifacts=False,
    )
    # Surcharge chemins clusters pour run_pipeline (via config default.yaml déjà OK)

    print("📊 Pipeline v2 — données réelles (comparaison GHSL)...")
    real_v2 = run_pipeline(
        feature_set="v2",
        use_fake=False,
        gee_parquet=PROJECT_ROOT / REAL_GEE,
        save_artifacts=False,
    )

    fake_baseline = _load_fake_baseline()
    comparison = _build_comparison(real_v3, real_v2, fake_baseline)
    assessment = _strengths_and_limits(real_v3, comparison)

    # Sauvegarder importance dédiée
    imp_df = pd.DataFrame(
        [{"feature": k, "gain": v} for k, v in real_v3["importance_gain"].items()]
    ).sort_values("gain", ascending=False)
    imp_path = reports_dir / "feature_importance_gain_real.csv"
    imp_df.to_csv(imp_path, index=False)

    # Figures
    scatter_path = reports_dir / "oof_scatter_real.png"
    importance_path = reports_dir / "feature_importance_real.png"
    from src.data.load_training_data import build_training_matrix
    from src.models.cv_pipeline import run_spatial_cv
    from src.utils.spatial_cv import select_cv_strategy

    X, y, meta = build_training_matrix(training_df, feature_cols=FEATURE_COLUMNS_BY_SET["v3"])
    cv_strategy, fold_ids, _ = select_cv_strategy(
        gdf,
        preferred=config["model"]["cv_strategy"],
        n_folds=config["model"]["n_folds"],
        random_state=config["model"]["random_state"],
    )
    cv_results = run_spatial_cv(X, y, gdf, config, cv_strategy=cv_strategy, return_models=False)
    _plot_oof_scatter(y, cv_results.oof_predictions, real_v3["metrics_oof"], scatter_path)
    _plot_importance(real_v3["importance_gain"], importance_path)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_source": "real_dhs_2018",
        "feature_set": "v3",
        "n_clusters": real_v3["n_clusters"],
        "cv_strategy": real_v3["cv_strategy"],
        "data_quality": data_qa,
        "metrics_oof": {k: round(v, 6) if isinstance(v, float) else v for k, v in real_v3["metrics_oof"].items()},
        "top10_importance": _importance_top10(real_v3["importance_gain"]),
        "correlations_abs_with_wealth": real_v3.get("correlations_abs"),
        "comparison": comparison,
        "assessment": assessment,
        "artifacts": {
            "results_json": str(PROJECT_ROOT / OUTPUT_JSON),
            "importance_csv": str(imp_path),
            "oof_scatter_png": str(scatter_path),
            "importance_png": str(importance_path),
        },
    }

    out_json = PROJECT_ROOT / OUTPUT_JSON
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if not skip_notebook:
        print("📓 Exécution notebook 02 (données réelles)...")
        run_notebook(
            feature_set="v3",
            use_fake=False,
            gee_parquet=PROJECT_ROOT / REAL_GEE,
            notebook_path=PROJECT_ROOT / "notebooks/02_modeling_pipeline.ipynb",
            output_path=PROJECT_ROOT / "notebooks/02_modeling_real_data_executed.ipynb",
            timeout=1200,
        )

    return report


def _print_report(report: dict) -> None:
    m = report["metrics_oof"]
    print("\n" + "=" * 70)
    print("MODÉLISATION — DONNÉES RÉELLES DHS 2018 (v3)")
    print("=" * 70)
    print(f"Grappes      : {report['n_clusters']}")
    print(f"CV           : {report['cv_strategy']}")
    print(f"R² OOF       : {m['r2']:.4f}")
    print(f"Spearman OOF : {m['spearman']:.4f}")
    print(f"RMSE OOF     : {m['rmse']:.2f}")
    print(f"MAE OOF      : {m.get('mae', 'n/a')}")
    print("\nTop 5 features (gain) :")
    for row in report["top10_importance"][:5]:
        print(f"  {row['rank']:2d}. {row['feature']:<22} {row['gain']:.2f}")
    comp = report["comparison"]["real_vs_fake_v3"]
    if comp.get("delta_real_minus_fake"):
        d = comp["delta_real_minus_fake"]
        print(f"\nΔ vs fake v3 : R² {d['r2']:+.3f}, Spearman {d['spearman']:+.3f}")
    print(f"\nRapport : {report['artifacts']['results_json']}")
    print("=" * 70)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Évaluation modèle sur vraies DHS")
    p.add_argument("--skip-notebook", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    report = run_real_evaluation(skip_notebook=args.skip_notebook)
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())