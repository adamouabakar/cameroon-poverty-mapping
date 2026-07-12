#!/usr/bin/env python
"""
Génère un rapport PDF professionnel pour ONG partenaires.

Usage:
  python scripts/generate_ngo_pdf_report.py
  python scripts/generate_ngo_pdf_report.py --region "Extrême-Nord"
  python scripts/generate_ngo_pdf_report.py --output outputs/reports/ngo_report_extreme_nord.pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.reports.pdf_report import generate_ngo_pdf_report
from src.reports.region_stats import DHS_REGIONS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rapport PDF ONG")
    p.add_argument("--region", default="Tout le Cameroun", choices=DHS_REGIONS)
    p.add_argument(
        "--output",
        default="outputs/reports/ngo_report_cameroon.pdf",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = PROJECT_ROOT / args.output
    generate_ngo_pdf_report(PROJECT_ROOT, region=args.region, output_path=out)
    print(f"✅ Rapport PDF généré : {out}")
    print(f"   Région : {args.region}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())