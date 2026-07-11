#!/usr/bin/env python
"""Prépare data/processed/ins_contextual_data.parquet depuis les sources INS brutes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ins.load_ins import load_ins_contextual_data


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Préparer données contextuelles INS")
    p.add_argument("--raw", default="data/reference/ins/ecam4_regional_indicators.csv")
    p.add_argument("--output", default="data/processed/ins_contextual_data.parquet")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    df = load_ins_contextual_data(
        raw_path=args.raw,
        output_path=args.output,
        project_root=PROJECT_ROOT,
    )
    print("✅ Données INS contextuelles prêtes")
    print(f"  Régions : {len(df)}")
    print(f"  Sortie  : {args.output}")
    print(df[["region_dhs", "poverty_rate_pct", "literacy_rate_15plus_pct"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())