#!/usr/bin/env python
"""
Prépare les grappes DHS Cameroun 2018 réelles (GPS + HR → parquet + QA).

Usage :
  python scripts/prepare_real_dhs_clusters.py
  python scripts/prepare_real_dhs_clusters.py --dhs-dir data/raw/dhs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.prepare_real_dhs import prepare_real_dhs_clusters


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Préparer grappes DHS réelles")
    p.add_argument("--dhs-dir", default="data/raw/dhs")
    p.add_argument(
        "--output",
        default="data/processed/dhs_clusters_real.parquet",
    )
    p.add_argument(
        "--qa-report",
        default="outputs/reports/dhs_real_qa.json",
    )
    p.add_argument("--random-state", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    gdf, qa = prepare_real_dhs_clusters(
        dhs_dir=PROJECT_ROOT / args.dhs_dir,
        output_path=PROJECT_ROOT / args.output,
        qa_report_path=PROJECT_ROOT / args.qa_report,
        random_state=args.random_state,
        project_root=PROJECT_ROOT,
    )
    print("\n" + "=" * 60)
    print("DHS RÉEL — PRÉPARATION TERMINÉE")
    print("=" * 60)
    print(f"Grappes        : {qa['n_clusters']}")
    print(f"Urbain / rural : {qa['urban_rural_counts']}")
    print(f"Wealth (méd.)  : {qa['wealth_index_stats']['median']:.1f}")
    print(f"QA passed      : {qa['qa_passed']}")
    print(f"Sortie         : {args.output}")
    print("=" * 60)
    return 0 if qa["qa_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())