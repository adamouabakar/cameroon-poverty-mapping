#!/usr/bin/env python
"""
Compare objectivement feature_set v1 (WorldCover) vs v2 (GHSL).

Produit : outputs/reports/v1_vs_v2_comparison.json

Usage :
  python scripts/compare_v1_v2_ghsl.py
  python scripts/compare_v1_v2_ghsl.py --skip-extraction   # si parquets déjà présents
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

V1_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_v1.parquet"
V2_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee.parquet"
OUTPUT_JSON = PROJECT_ROOT / "outputs/reports/v1_vs_v2_comparison.json"

BUILT_COL = {"v1": "built_density", "v2": "ghsl_built_fraction"}


def _load_raw_gee_config() -> dict:
    import yaml
    from src.features.gee.config import resolve_feature_set

    with open(PROJECT_ROOT / "configs/gee.yaml", encoding="utf-8") as f:
        raw = yaml.safe_load(f)["gee"]
    raw["_base_feature_columns"] = list(raw["feature_columns"])
    raw["_base_band_names"] = dict(raw["band_names"])
    return raw


def extract_v1_features(clusters_path: Path) -> None:
    """Extrait les features GEE en mode v1 (WorldCover built_density)."""
    from src.features.gee.client import initialize_gee
    from src.features.gee.config import resolve_feature_set
    from src.features.gee.extract_clusters import extract_from_clusters_file

    raw = _load_raw_gee_config()
    config_v1 = resolve_feature_set({**raw, "feature_set": "v1"})

    print("🛰️  Extraction GEE v1 (WorldCover built_density)...")
    initialize_gee(project_id=config_v1.get("project_id"))
    df = extract_from_clusters_file(clusters_path, config_v1, mode="clusters")
    V1_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(V1_PARQUET, index=False)
    print(f"   → {len(df)} grappes sauvegardées : {V1_PARQUET}")


def _importance_rank(importance: dict, feature: str) -> int | None:
    if not importance:
        return None
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    for i, (name, _) in enumerate(ranked, start=1):
        if name == feature:
            return i
    return None


def build_comparison(v1: dict, v2: dict) -> dict:
    """Construit le rapport comparatif et la conclusion."""
    m1, m2 = v1["metrics_oof"], v2["metrics_oof"]
    b1, b2 = BUILT_COL["v1"], BUILT_COL["v2"]

    delta = {
        "r2": round(m2["r2"] - m1["r2"], 4),
        "spearman": round(m2["spearman"] - m1["spearman"], 4),
        "rmse": round(m2["rmse"] - m1["rmse"], 4),
    }

    imp_v1 = v1.get("importance_gain", {})
    imp_v2 = v2.get("importance_gain", {})

    table = {
        "metric": ["R² OOF", "Spearman OOF", "RMSE OOF", f"Gain {b1}", f"Gain {b2}", f"Rang {b1}", f"Rang {b2}"],
        "v1_worldcover": [
            round(m1["r2"], 4),
            round(m1["spearman"], 4),
            round(m1["rmse"], 4),
            round(imp_v1.get(b1, 0), 4),
            None,
            _importance_rank(imp_v1, b1),
            None,
        ],
        "v2_ghsl": [
            round(m2["r2"], 4),
            round(m2["spearman"], 4),
            round(m2["rmse"], 4),
            None,
            round(imp_v2.get(b2, 0), 4),
            None,
            _importance_rank(imp_v2, b2),
        ],
        "delta_v2_minus_v1": [
            delta["r2"],
            delta["spearman"],
            delta["rmse"],
            None,
            None,
            None,
            None,
        ],
    }

    # Conclusion heuristique (données fictives = signal faible attendu)
    r2_better = delta["r2"] > 0.01
    spearman_better = delta["spearman"] > 0.01
    ghsl_gain = imp_v2.get(b2, 0)
    worldcover_gain = imp_v1.get(b1, 0)

    if r2_better or spearman_better:
        verdict = "v2_ghsl_preferred"
        summary = (
            "GHSL (v2) améliore au moins une métrique OOF vs WorldCover (v1). "
            "Recommandé de conserver GHSL pour la suite (vraies DHS)."
        )
    elif abs(delta["r2"]) < 0.02 and abs(delta["spearman"]) < 0.02:
        verdict = "equivalent_on_fake_data"
        summary = (
            "Sur grappes fictives, v1 et v2 sont équivalents (écart métrique < 2 pts). "
            "GHSL reste préférable pour l'alignement temporel DHS 2018 ; valider sur vraies DHS."
        )
    else:
        verdict = "v1_slightly_better_on_fake"
        summary = (
            "WorldCover (v1) légèrement meilleur sur ces grappes fictives. "
            "Ne pas abandonner GHSL : réévaluer avec vraies grappes DHS 2018."
        )

    recommendations = [
        "Conserver feature_set v2 (GHSL) comme défaut — meilleur alignement temporel vs DHS 2018.",
        "Ré-exécuter cette comparaison après chargement des vraies grappes DHS (~300+).",
        f"Sur cet échantillon : gain GHSL={ghsl_gain:.2f}, gain WorldCover={worldcover_gain:.2f}.",
    ]
    if ghsl_gain == 0 and worldcover_gain == 0:
        recommendations.append(
            "Les deux features bâti ont gain LightGBM nul ici — normal avec wealth_index simulé."
        )

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_clusters": v1.get("n_clusters"),
        "cv_strategy": v1.get("cv_strategy"),
        "data_note": "Grappes et wealth_index fictifs (Notebook 01) — comparaison structurelle.",
        "parquet_v1": str(V1_PARQUET),
        "parquet_v2": str(V2_PARQUET),
        "comparison_table": table,
        "delta_v2_minus_v1": delta,
        "v1_detail": v1,
        "v2_detail": v2,
        "verdict": verdict,
        "conclusion": summary,
        "recommendations": recommendations,
    }


def print_comparison(report: dict) -> None:
    print("\n" + "=" * 70)
    print("COMPARAISON v1 (WorldCover) vs v2 (GHSL)")
    print("=" * 70)
    t = report["comparison_table"]
    rows = zip(t["metric"], t["v1_worldcover"], t["v2_ghsl"], t["delta_v2_minus_v1"])
    print(f"{'Métrique':<22} {'v1':>12} {'v2':>12} {'Δ(v2-v1)':>12}")
    print("-" * 70)
    for metric, v1, v2, d in rows:
        v1s = f"{v1:.4f}" if isinstance(v1, float) else str(v1)
        v2s = f"{v2:.4f}" if isinstance(v2, float) else str(v2)
        ds = f"{d:+.4f}" if isinstance(d, float) else str(d)
        print(f"{metric:<22} {v1s:>12} {v2s:>12} {ds:>12}")
    print("-" * 70)
    print(f"Verdict : {report['verdict']}")
    print(f"Conclusion : {report['conclusion']}")
    print("Recommandations :")
    for r in report["recommendations"]:
        print(f"  • {r}")
    print(f"\nRapport JSON : {OUTPUT_JSON}")
    print("=" * 70)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Comparer feature_set v1 vs v2")
    p.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Ne pas ré-extraire v1 via GEE (utiliser parquet existant)",
    )
    p.add_argument(
        "--clusters",
        default="data/processed/dhs_prepared_with_buffers.parquet",
    )
    return p.parse_args()


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from run_notebook_02_pipeline import run_pipeline

    args = parse_args()
    clusters_path = PROJECT_ROOT / args.clusters

    if not V2_PARQUET.exists():
        print(f"❌ Parquet v2 introuvable : {V2_PARQUET}")
        return 1

    if not args.skip_extraction or not V1_PARQUET.exists():
        extract_v1_features(clusters_path)
    else:
        print(f"ℹ️  Parquet v1 existant : {V1_PARQUET}")

    print("\n📊 Pipeline v1 (WorldCover)...")
    v1_result = run_pipeline(
        feature_set="v1",
        gee_parquet=V1_PARQUET,
        save_artifacts=False,
    )

    print("\n📊 Pipeline v2 (GHSL)...")
    v2_result = run_pipeline(
        feature_set="v2",
        gee_parquet=V2_PARQUET,
        save_artifacts=False,
    )

    report = build_comparison(v1_result, v2_result)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print_comparison(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())