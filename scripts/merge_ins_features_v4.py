#!/usr/bin/env python
"""
Fusionne features GEE v3 + indicateurs INS régionaux → feature set v4 (niveau grappe).

Sortie : data/processed/features/cluster_features_gee_ins_v4.parquet
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ins.load_ins import load_ins_contextual_data
from src.ins.merge_features import merge_ins_to_feature_parquet
from src.ins.regions import INS_FEATURE_COLUMNS_V4


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merger features GEE v3 + INS v4")
    p.add_argument(
        "--features",
        default="data/processed/features/cluster_features_gee_real.parquet",
    )
    p.add_argument("--clusters", default="data/processed/dhs_clusters_real.parquet")
    p.add_argument("--ins", default="data/processed/ins_contextual_data.parquet")
    p.add_argument(
        "--output",
        default="data/processed/features/cluster_features_gee_ins_v4.parquet",
    )
    p.add_argument("--report", default="outputs/reports/ins_feature_set_v4.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    ins_path = PROJECT_ROOT / args.ins
    if not ins_path.exists():
        load_ins_contextual_data(project_root=PROJECT_ROOT)
    ins_df = __import__("pandas").read_parquet(ins_path)

    out = merge_ins_to_feature_parquet(
        PROJECT_ROOT / args.features,
        ins_df,
        PROJECT_ROOT / args.clusters,
        PROJECT_ROOT / args.output,
    )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_set": "v4",
        "base_features": "gee_v3",
        "ins_columns": INS_FEATURE_COLUMNS_V4,
        "n_rows": int(len(out)),
        "n_columns": int(len(out.columns)),
        "output": args.output,
        "source_ins": "ECAM 4 (INS, 2014)",
        "note": "Variables INS régionales jointes par region DHS — pas d'extraction GEE supplémentaire.",
    }
    report_path = PROJECT_ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("✅ Feature set v4 (GEE v3 + INS) prêt")
    print(f"  Lignes   : {len(out)}")
    print(f"  Colonnes INS ajoutées : {INS_FEATURE_COLUMNS_V4}")
    print(f"  Sortie   : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())