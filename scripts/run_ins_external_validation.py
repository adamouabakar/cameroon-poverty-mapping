#!/usr/bin/env python
"""
Validation externe du modèle vs statistiques officielles INS (ECAM 4).

Produit :
  - outputs/reports/ins_external_validation.json
  - outputs/reports/ins_external_validation_table.csv
  - outputs/maps/ins_external_validation_scatter.png
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

from src.ins.load_ins import load_ins_contextual_data
from src.ins.validate_external import (
    aggregate_predictions_by_region,
    build_validation_table,
    compute_validation_metrics,
    plot_validation_scatter,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validation externe INS")
    p.add_argument("--clusters", default="data/processed/dhs_clusters_real.parquet")
    p.add_argument("--oof", default="data/processed/training/oof_predictions.parquet")
    p.add_argument("--ins", default="data/processed/ins_contextual_data.parquet")
    p.add_argument("--report", default="outputs/reports/ins_external_validation.json")
    p.add_argument("--table", default="outputs/reports/ins_external_validation_table.csv")
    p.add_argument("--plot", default="outputs/maps/ins_external_validation_scatter.png")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    ins_path = PROJECT_ROOT / args.ins
    if not ins_path.exists():
        load_ins_contextual_data(project_root=PROJECT_ROOT)

    clusters = gpd.read_parquet(PROJECT_ROOT / args.clusters)
    oof = pd.read_parquet(PROJECT_ROOT / args.oof)
    ins_df = pd.read_parquet(ins_path)

    regional = aggregate_predictions_by_region(clusters, oof)
    table = build_validation_table(regional, ins_df)
    metrics = compute_validation_metrics(table)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_ins": {
            "survey": "ECAM 4",
            "producer": "INS Cameroun",
            "year": 2014,
            "citation": "INS (2014). 4e Enquête Camerounaise auprès des Ménages.",
            "raw_file": "data/raw/ins/ecam4_regional_indicators.csv",
        },
        "model_reference": {
            "clusters": args.clusters,
            "oof_predictions": args.oof,
            "pred_col": "y_oof_pred",
            "note": "Prédictions OOF LightGBM v3 — proxy richesse DHS, pas pauvreté monétaire.",
        },
        "metrics": metrics,
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
    }

    report_path = PROJECT_ROOT / args.report
    table_path = PROJECT_ROOT / args.table
    plot_path = PROJECT_ROOT / args.plot
    report_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    table.to_csv(table_path, index=False)
    plot_validation_scatter(table, plot_path)

    print("✅ Validation externe INS terminée")
    print(f"  Régions comparées : {metrics['n_regions']}")
    print(f"  Spearman (wealth vs pauvreté) : {metrics['spearman_wealth_vs_poverty']:.3f}")
    print(f"  Écart rang moyen : {metrics['mean_rank_gap']:.2f}")
    print(f"  Rapport : {report_path}")
    print(f"  Tableau : {table_path}")
    print(f"  Graphique : {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())