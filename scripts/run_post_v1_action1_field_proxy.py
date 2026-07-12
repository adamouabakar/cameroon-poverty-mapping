#!/usr/bin/env python
"""
Post-v1.0 Action 1 — Validation terrain proxy (données publiques).

Compare DHS 2018 cluster wealth (ground-truth proxy) to OOF predictions
and national rasters; cross-check INS ECAM 4 regional metrics.

Outputs:
  - partner_pack/field_data/sites_proxy.csv
  - outputs/reports/field_validation_proxy.json
  - outputs/reports/field_validation_proxy.md
  - outputs/maps/field_validation_proxy_scatter.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import pandas as pd

from src.validation.field_proxy import (
    build_proxy_sites,
    plot_proxy_scatter,
    write_proxy_csv,
    write_proxy_report,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post-v1 Action 1 — field proxy validation")
    p.add_argument("--clusters", default="data/processed/dhs_clusters_real.parquet")
    p.add_argument("--oof", default="data/processed/training/oof_predictions.parquet")
    p.add_argument(
        "--wealth",
        default="outputs/maps/wealth_index_predicted_1km_model_v4.tif",
    )
    p.add_argument(
        "--uncertainty",
        default="outputs/maps/wealth_uncertainty_1km_model_v4.tif",
    )
    p.add_argument(
        "--csv",
        default="partner_pack/field_data/sites_proxy.csv",
    )
    p.add_argument(
        "--report-json",
        default="outputs/reports/field_validation_proxy.json",
    )
    p.add_argument(
        "--report-md",
        default="outputs/reports/field_validation_proxy.md",
    )
    p.add_argument(
        "--plot",
        default="outputs/maps/field_validation_proxy_scatter.png",
    )
    p.add_argument("--min-per-region", type=int, default=1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--ins-report",
        default="outputs/reports/ins_external_validation.json",
        help="Optional INS ECAM4 cross-check JSON",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    clusters = gpd.read_parquet(PROJECT_ROOT / args.clusters)
    oof = pd.read_parquet(PROJECT_ROOT / args.oof)
    wealth = PROJECT_ROOT / args.wealth
    uncertainty = PROJECT_ROOT / args.uncertainty

    if not wealth.is_file():
        fallback = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model_z.tif"
        if fallback.is_file():
            wealth = fallback
        else:
            print(f"ERROR: wealth raster missing: {wealth}", file=sys.stderr)
            return 1
    if not uncertainty.is_file():
        fallback = PROJECT_ROOT / "outputs/maps/wealth_uncertainty_1km_model.tif"
        uncertainty = fallback if fallback.is_file() else uncertainty

    sites, metrics = build_proxy_sites(
        clusters,
        oof,
        wealth_path=wealth,
        uncertainty_path=uncertainty,
        min_per_region=args.min_per_region,
        seed=args.seed,
    )

    ins_metrics = None
    ins_path = PROJECT_ROOT / args.ins_report
    if ins_path.is_file():
        ins_raw = json.loads(ins_path.read_text(encoding="utf-8"))
        ins_metrics = ins_raw.get("metrics")

    csv_path = PROJECT_ROOT / args.csv
    write_proxy_csv(sites, csv_path)
    write_proxy_report(
        sites,
        metrics,
        out_json=PROJECT_ROOT / args.report_json,
        out_md=PROJECT_ROOT / args.report_md,
        ins_metrics=ins_metrics,
    )
    plot_proxy_scatter(sites, PROJECT_ROOT / args.plot)

    print("✅ Post-v1 Action 1 — validation terrain proxy terminée")
    print(f"  Sites proxy : {int(metrics['n_sites'])} ({int(metrics['n_regions'])} régions)")
    print(f"  Spearman OOF vs DHS : {metrics['spearman_oof_vs_dhs']:.3f}")
    if "spearman_raster_vs_dhs" in metrics:
        print(f"  Spearman raster vs DHS : {metrics['spearman_raster_vs_dhs']:.3f}")
    print(f"  Concordance match : {metrics['concordance_match_pct']:.1f}%")
    print(f"  CSV : {csv_path}")
    print(f"  Rapport : {PROJECT_ROOT / args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())