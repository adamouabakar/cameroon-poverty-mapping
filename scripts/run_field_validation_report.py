#!/usr/bin/env python
"""Validate field site CSV, sample national rasters, write discrepancy report.

Usage:
  python scripts/run_field_validation_report.py \\
    --csv partner_pack/field_data/sites.csv \\
    --partner "Université X / contact" \\
    --workshop-date 2026-07-20 \\
    --workshop-minutes 60 \\
    --region Littoral

MVP gate: ≥5 non-example site rows required unless --allow-partial.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.partner_web.claims import default_input_paths, load_claims  # noqa: E402
from src.partner_web.field_validation import (  # noqa: E402
    FieldValidationError,
    enrich_with_rasters,
    load_sites_csv,
    validate_mvp_count,
    write_reports,
)
from src.partner_web.render import load_master_wealth, warp_to_master  # noqa: E402
from rasterio.warp import Resampling  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Field validation MVP report")
    p.add_argument(
        "--csv",
        default=str(PROJECT_ROOT / "partner_pack" / "field_data" / "sites.csv"),
    )
    p.add_argument("--partner", required=True, help="Partner org / person (may be public)")
    p.add_argument("--workshop-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--workshop-minutes", type=int, default=60)
    p.add_argument("--region", default="", help="Region focus label")
    p.add_argument(
        "--out-md",
        default="",
        help="Default: outputs/reports/field_validation_YYYY-MM-DD.md",
    )
    p.add_argument("--out-json", default="")
    p.add_argument("--claims", default=str(PROJECT_ROOT / "configs" / "claims.yaml"))
    p.add_argument("--wealth", default="")
    p.add_argument("--uncertainty", default="")
    p.add_argument(
        "--allow-partial",
        action="store_true",
        help="Skip ≥5 sites MVP gate (for dry-runs)",
    )
    p.add_argument("--notes", default="", help="Extra free-text workshop notes")
    p.add_argument(
        "--map-url",
        default="",
        help="Override map URL (default from claims.map_url)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)

    try:
        claims = load_claims(Path(args.claims))
        paths = default_input_paths(PROJECT_ROOT, claims)
        wealth = Path(args.wealth) if args.wealth else paths["wealth"]
        unc = Path(args.uncertainty) if args.uncertainty else paths["uncertainty"]

        rows = load_sites_csv(csv_path)
        if not args.allow_partial:
            validate_mvp_count(rows, minimum=5)

        # Reference terciles from downsampled national wealth (consistent with web map)
        wealth_arr, transform, crs = load_master_wealth(wealth, max_edge=512)
        unc_arr = warp_to_master(
            unc,
            transform,
            crs,
            wealth_arr.shape[0],
            wealth_arr.shape[1],
            resampling=Resampling.bilinear,
        )
        enrich_with_rasters(rows, wealth, unc, wealth_ref=wealth_arr, unc_ref=unc_arr)

        day = args.workshop_date
        out_md = (
            Path(args.out_md)
            if args.out_md
            else PROJECT_ROOT / "outputs" / "reports" / f"field_validation_{day}.md"
        )
        out_json = (
            Path(args.out_json)
            if args.out_json
            else PROJECT_ROOT / "outputs" / "reports" / f"field_validation_{day}.json"
        )
        map_url = (
            args.map_url
            or (claims.get("map_url") or "").strip()
            or "https://adamouabakar.github.io/cameroon-poverty-mapping/"
        )

        write_reports(
            rows,
            out_md,
            out_json,
            partner=args.partner,
            workshop_date=args.workshop_date,
            workshop_minutes=args.workshop_minutes,
            region_focus=args.region,
            map_url=map_url,
            extra_notes=args.notes,
        )
        print(f"OK wrote {out_md}")
        print(f"OK wrote {out_json}")
        print(f"sites={len(rows)}")
        return 0
    except FieldValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
