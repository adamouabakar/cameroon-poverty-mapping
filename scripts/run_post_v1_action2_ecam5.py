#!/usr/bin/env python
"""
Post-v1.0 Action 2 — Intégration ECAM 5 + micro-données (sources publiques).

1. Charge indicateurs régionaux ECAM 5 (INS 2022)
2. Validation externe modèle vs ECAM5
3. Fusion features GEE + ECAM5 (preview)
4. Rapport micro-données + comparaison ECAM4/ECAM5
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import pandas as pd

from src.ins.load_ecam5 import (
    ECAM5_NATIONAL_2022,
    load_ecam5_contextual_data,
    microdata_availability_report,
)
from src.ins.merge_features import merge_ins_to_feature_parquet
from src.ins.regions import INS_FEATURE_COLUMNS_V4
from src.ins.validate_external import (
    aggregate_predictions_by_region,
    build_validation_table,
    compute_validation_metrics,
    plot_validation_scatter,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post-v1 Action 2 — ECAM5 integration")
    p.add_argument("--clusters", default="data/processed/dhs_clusters_real.parquet")
    p.add_argument("--oof", default="data/processed/training/oof_predictions.parquet")
    p.add_argument("--ecam5-raw", default="data/reference/ins/ecam5_regional_indicators.csv")
    p.add_argument("--ecam5-parquet", default="data/processed/ins_contextual_ecam5.parquet")
    p.add_argument(
        "--features-out",
        default="data/processed/features/cluster_features_gee_ins_ecam5.parquet",
    )
    p.add_argument("--report", default="outputs/reports/post_v1_action2_ecam5.json")
    p.add_argument("--report-md", default="outputs/reports/post_v1_action2_ecam5.md")
    p.add_argument(
        "--plot",
        default="outputs/maps/ins_ecam5_external_validation_scatter.png",
    )
    return p.parse_args()


def _load_ecam4_metrics(project_root: Path) -> dict | None:
    path = project_root / "outputs/reports/ins_external_validation.json"
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("metrics")


def main() -> int:
    args = parse_args()

    ins_df = load_ecam5_contextual_data(
        raw_path=args.ecam5_raw,
        output_path=args.ecam5_parquet,
        project_root=PROJECT_ROOT,
    )

    clusters = gpd.read_parquet(PROJECT_ROOT / args.clusters)
    oof = pd.read_parquet(PROJECT_ROOT / args.oof)

    regional = aggregate_predictions_by_region(clusters, oof)
    table = build_validation_table(regional, ins_df)
    metrics = compute_validation_metrics(table)

    plot_path = PROJECT_ROOT / args.plot
    plot_validation_scatter(table, plot_path)

    gee_features = PROJECT_ROOT / "data/processed/features/cluster_features_gee_real.parquet"
    features_out = merge_ins_to_feature_parquet(
        gee_features,
        ins_df,
        PROJECT_ROOT / args.clusters,
        PROJECT_ROOT / args.features_out,
    )

    ecam4_metrics = _load_ecam4_metrics(PROJECT_ROOT)
    micro = microdata_availability_report()

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "action": "post_v1_action2_ecam5",
        "source_ins": {
            "survey": "ECAM 5",
            "producer": "INS Cameroun",
            "year": 2022,
            "citation": "INS (2024). ECAM 5 — Principaux indicateurs (dépliant).",
            "raw_file": args.ecam5_raw,
            "national_indicators_2022": ECAM5_NATIONAL_2022,
        },
        "model_reference": {
            "clusters": args.clusters,
            "oof_predictions": args.oof,
            "pred_col": "y_oof_pred",
        },
        "metrics_ecam5": metrics,
        "metrics_ecam4_baseline": ecam4_metrics,
        "comparison_table": table[
            [
                "region",
                "n_clusters",
                "mean_predicted_wealth",
                "poverty_rate_pct",
                "literacy_rate_15plus_pct",
                "electricity_access_pct",
                "wealth_rank",
                "poverty_rank",
                "rank_gap",
            ]
        ].to_dict(orient="records"),
        "microdata": micro,
        "artifacts": {
            "ins_contextual_ecam5": args.ecam5_parquet,
            "features_gee_ins_ecam5": args.features_out,
            "validation_plot": str(plot_path.relative_to(PROJECT_ROOT)),
            "n_feature_rows": int(len(features_out)),
            "ins_columns": INS_FEATURE_COLUMNS_V4,
        },
        "limitations": [
            "Micro-données ECAM5 unitaires non publiques — indicateurs régionaux + DHS proxy.",
            "Pauvreté régionale ECAM5 partiellement estimée (voir poverty_source dans CSV).",
            "ECAM5 méthodologie EHCVM ≠ ECAM4 — comparer surtout les rangs régionaux.",
            "DHS 2018 vs ECAM 2022 — décalage temporel ~4 ans.",
        ],
    }

    report_path = PROJECT_ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# Post-v1.0 Action 2 — Intégration ECAM 5",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC*",
        "",
        "## Sources publiques intégrées",
        "",
        f"- **ECAM 5 (2022)** : `{args.ecam5_raw}`",
        f"- **Indicateurs nationaux** : pauvreté {ECAM5_NATIONAL_2022['poverty_rate_pct']}%, "
        f"alphabétisation {ECAM5_NATIONAL_2022['literacy_rate_15plus_pct']}%",
        f"- **Micro-données proxy** : DHS 2018 — 430 grappes",
        "",
        "## Validation externe (modèle v4 OOF vs ECAM5)",
        "",
        f"| Métrique | ECAM5 | ECAM4 (baseline) |",
        f"|----------|-------|------------------|",
        f"| Spearman wealth↔pauvreté | {metrics['spearman_wealth_vs_poverty']:.3f} | "
        f"{(ecam4_metrics or {}).get('spearman_wealth_vs_poverty', float('nan')):.3f} |",
        f"| Écart rang moyen | {metrics['mean_rank_gap']:.2f} | "
        f"{(ecam4_metrics or {}).get('mean_rank_gap', float('nan')):.2f} |",
        f"| Régions | {metrics['n_regions']} | "
        f"{(ecam4_metrics or {}).get('n_regions', '—')} |",
        "",
        "## Livrables",
        "",
        f"- `{args.ecam5_parquet}`",
        f"- `{args.features_out}` ({len(features_out)} lignes)",
        f"- `{args.report}`",
        "",
        "## Micro-données ECAM5",
        "",
        "Les fichiers unitaires ECAM5 **ne sont pas** en libre accès public. "
        "Le pipeline utilise les tableaux régionaux INS + grappes DHS comme proxy micro.",
        "",
    ]
    md_path = PROJECT_ROOT / args.report_md
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    table_csv = PROJECT_ROOT / "outputs/reports/ins_ecam5_external_validation_table.csv"
    table.to_csv(table_csv, index=False)

    print("✅ Post-v1 Action 2 — intégration ECAM 5 terminée")
    print(f"  Régions ECAM5 : {len(ins_df)}")
    print(f"  Spearman wealth↔pauvreté (ECAM5) : {metrics['spearman_wealth_vs_poverty']:.3f}")
    print(f"  Features : {args.features_out}")
    print(f"  Rapport : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())