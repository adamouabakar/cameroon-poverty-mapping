#!/usr/bin/env python
"""
Génère un rapport PDF professionnel pour ONG partenaires (Phase 3).

Usage:
  python scripts/generate_ngo_pdf_report.py
  python scripts/generate_ngo_pdf_report.py --region "Extrême-Nord"
  python scripts/generate_ngo_pdf_report.py --lang en --config configs/ngo_report.yaml
  python scripts/generate_ngo_pdf_report.py --field-csv partner_pack/field_data/sites_proxy.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.reports.pdf_report import generate_ngo_pdf_report
from src.reports.region_stats import DHS_REGIONS
from src.reports.report_config import ReportOptions, load_report_config


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rapport PDF ONG (Phase 3)")
    p.add_argument("--region", default="Tout le Cameroun", choices=DHS_REGIONS)
    p.add_argument(
        "--output",
        default="outputs/reports/ngo_report_cameroon.pdf",
    )
    p.add_argument("--lang", choices=["fr", "en"], default=None, help="Langue du rapport")
    p.add_argument(
        "--config",
        default=None,
        help="Chemin YAML (défaut: configs/ngo_report.yaml)",
    )
    p.add_argument(
        "--field-csv",
        default=None,
        help="CSV validation terrain (remplace default_csv du config)",
    )
    p.add_argument(
        "--no-section",
        action="append",
        default=[],
        metavar="KEY",
        help="Désactiver une section (ex: shap, maps)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg_path = Path(args.config) if args.config else None
    opts = load_report_config(cfg_path, project_root=PROJECT_ROOT)

    if args.lang:
        opts.language = args.lang
    opts.region = args.region

    if args.field_csv:
        field = PROJECT_ROOT / args.field_csv
        opts.field_csv = field if field.is_file() else None

    for key in args.no_section:
        if key in opts.sections:
            opts.sections[key] = False

    out = PROJECT_ROOT / args.output
    generate_ngo_pdf_report(PROJECT_ROOT, region=args.region, output_path=out, options=opts)
    print(f"✅ Rapport PDF généré : {out}")
    print(f"   Région : {args.region}")
    print(f"   Langue : {opts.language}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())