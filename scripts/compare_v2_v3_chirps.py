#!/usr/bin/env python
"""
Compare objectivement feature_set v2 (GHSL) vs v3 (GHSL + CHIRPS).

Produit : outputs/reports/v2_vs_v3_comparison.json

Usage :
  python scripts/compare_v2_v3_chirps.py
  python scripts/compare_v2_v3_chirps.py --run-notebooks   # exécute aussi le notebook v3
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

V2_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee.parquet"
V3_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_v3.parquet"
OUTPUT_JSON = PROJECT_ROOT / "outputs/reports/v2_vs_v3_comparison.json"

CHIRPS_COLS = ("precip_annual_mm", "precip_wet_season_mm", "precip_cv")


def _importance_rank(importance: dict, feature: str) -> int | None:
    if not importance:
        return None
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for i, (name, _) in enumerate(ranked, start=1):
        if name == feature:
            return i
    return None


def build_comparison(v2: dict, v3: dict) -> dict:
    """Construit le rapport comparatif et la conclusion."""
    m2, m3 = v2["metrics_oof"], v3["metrics_oof"]
    delta = {
        "r2": round(m3["r2"] - m2["r2"], 4),
        "spearman": round(m3["spearman"] - m2["spearman"], 4),
        "rmse": round(m3["rmse"] - m2["rmse"], 4),
    }

    imp_v2 = v2.get("importance_gain", {})
    imp_v3 = v3.get("importance_gain", {})

    metrics = ["R² OOF", "Spearman OOF", "RMSE OOF"]
    v2_vals = [
        round(m2["r2"], 4),
        round(m2["spearman"], 4),
        round(m2["rmse"], 4),
    ]
    v3_vals = [
        round(m3["r2"], 4),
        round(m3["spearman"], 4),
        round(m3["rmse"], 4),
    ]
    delta_vals = [delta["r2"], delta["spearman"], delta["rmse"]]

    for col in CHIRPS_COLS:
        metrics.append(f"Gain {col}")
        v2_vals.append(None)
        v3_vals.append(round(imp_v3.get(col, 0), 4))
        delta_vals.append(None)

    for col in CHIRPS_COLS:
        metrics.append(f"Rang {col}")
        v2_vals.append(None)
        v3_vals.append(_importance_rank(imp_v3, col))
        delta_vals.append(None)

    table = {
        "metric": metrics,
        "v2_ghsl": v2_vals,
        "v3_ghsl_chirps": v3_vals,
        "delta_v3_minus_v2": delta_vals,
    }

    chirps_gains = {c: imp_v3.get(c, 0) for c in CHIRPS_COLS}
    chirps_ranks = {c: _importance_rank(imp_v3, c) for c in CHIRPS_COLS}
    any_chirps_gain = any(g > 0 for g in chirps_gains.values())
    r2_better = delta["r2"] > 0.01
    spearman_better = delta["spearman"] > 0.01
    metrics_unchanged = abs(delta["r2"]) < 0.02 and abs(delta["spearman"]) < 0.02

    if r2_better or spearman_better:
        verdict = "v3_chirps_preferred"
        summary = (
            "CHIRPS (v3) améliore au moins une métrique OOF vs v2 (GHSL seul). "
            "Recommandé de conserver v3 pour la suite (vraies DHS)."
        )
    elif metrics_unchanged and not any_chirps_gain:
        verdict = "equivalent_on_fake_data"
        summary = (
            "Sur grappes fictives, v2 et v3 sont équivalents (écart métrique < 2 pts) "
            "et les features CHIRPS ont un gain LightGBM nul. "
            "CHIRPS reste pertinent pour la richesse écologique du modèle ; valider sur vraies DHS."
        )
    elif metrics_unchanged and any_chirps_gain:
        verdict = "chirps_signal_no_metric_gain"
        summary = (
            "Métriques OOF inchangées mais au moins une feature CHIRPS a un gain > 0. "
            "Conserver v3 et réévaluer sur vraies grappes DHS 2018."
        )
    else:
        verdict = "v2_slightly_better_on_fake"
        summary = (
            "v2 (GHSL seul) légèrement meilleur sur ces grappes fictives. "
            "Ne pas abandonner CHIRPS : réévaluer avec vraies grappes DHS 2018."
        )

    recommendations = [
        "Conserver feature_set v3 comme option Phase 1 — précipitations alignées DHS 2018.",
        "Ré-exécuter cette comparaison après chargement des vraies grappes DHS (~300+).",
        f"Gains CHIRPS v3 : annual={chirps_gains['precip_annual_mm']:.2f}, "
        f"wet={chirps_gains['precip_wet_season_mm']:.2f}, "
        f"cv={chirps_gains['precip_cv']:.2f}.",
    ]
    if not any_chirps_gain:
        recommendations.append(
            "Gain LightGBM nul pour les 3 colonnes CHIRPS — attendu avec wealth_index simulé."
        )

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_clusters": v2.get("n_clusters"),
        "cv_strategy": v2.get("cv_strategy"),
        "data_note": "Grappes et wealth_index fictifs (Notebook 01) — comparaison structurelle.",
        "parquet_v2": str(V2_PARQUET),
        "parquet_v3": str(V3_PARQUET),
        "comparison_table": table,
        "delta_v3_minus_v2": delta,
        "chirps_importance": {
            "gain": chirps_gains,
            "rank": chirps_ranks,
        },
        "v2_detail": v2,
        "v3_detail": v3,
        "verdict": verdict,
        "conclusion": summary,
        "recommendations": recommendations,
    }


def print_comparison(report: dict) -> None:
    print("\n" + "=" * 72)
    print("COMPARAISON v2 (GHSL) vs v3 (GHSL + CHIRPS)")
    print("=" * 72)
    t = report["comparison_table"]
    rows = zip(t["metric"], t["v2_ghsl"], t["v3_ghsl_chirps"], t["delta_v3_minus_v2"])
    print(f"{'Métrique':<28} {'v2':>12} {'v3':>12} {'Δ(v3-v2)':>12}")
    print("-" * 72)
    for metric, v2, v3, d in rows:
        v2s = f"{v2:.4f}" if isinstance(v2, float) else str(v2)
        v3s = f"{v3:.4f}" if isinstance(v3, float) else str(v3)
        ds = f"{d:+.4f}" if isinstance(d, float) else str(d)
        print(f"{metric:<28} {v2s:>12} {v3s:>12} {ds:>12}")
    print("-" * 72)
    print(f"Verdict : {report['verdict']}")
    print(f"Conclusion : {report['conclusion']}")
    print("Recommandations :")
    for r in report["recommendations"]:
        print(f"  • {r}")
    print(f"\nRapport JSON : {OUTPUT_JSON}")
    print("=" * 72)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Comparer feature_set v2 vs v3")
    p.add_argument(
        "--skip-notebooks",
        action="store_true",
        help="Ne pas exécuter les notebooks (pipeline seulement)",
    )
    return p.parse_args()


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from run_notebook_02_pipeline import run_pipeline, run_notebook

    args = parse_args()

    if not V2_PARQUET.exists():
        print(f"❌ Parquet v2 introuvable : {V2_PARQUET}")
        return 1
    if not V3_PARQUET.exists():
        print(f"❌ Parquet v3 introuvable : {V3_PARQUET}")
        return 1

    print("\n📊 Pipeline v2 (GHSL)...")
    v2_result = run_pipeline(
        feature_set="v2",
        gee_parquet=V2_PARQUET,
        save_artifacts=False,
    )

    print("\n📊 Pipeline v3 (GHSL + CHIRPS)...")
    v3_result = run_pipeline(
        feature_set="v3",
        gee_parquet=V3_PARQUET,
        save_artifacts=False,
    )

    report = build_comparison(v2_result, v3_result)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print_comparison(report)

    if not args.skip_notebooks:
        print("\n📓 Notebook 02 — v2...")
        run_notebook(
            feature_set="v2",
            use_fake=False,
            gee_parquet=V2_PARQUET,
            output_path=PROJECT_ROOT / "notebooks" / "02_modeling_pipeline_executed_v2.ipynb",
        )
        print("\n📓 Notebook 02 — v3...")
        run_notebook(
            feature_set="v3",
            use_fake=False,
            gee_parquet=V3_PARQUET,
            output_path=PROJECT_ROOT / "notebooks" / "02_modeling_pipeline_executed.ipynb",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())