#!/usr/bin/env python
"""Build Partner Dialogue Pack site/ + partner_pack/.

Usage:
  python scripts/build_partner_web.py
  python scripts/build_partner_web.py --wealth path --priority path --uncertainty path
  python scripts/build_partner_web.py --fixtures   # use tests/fixtures tiny rasters

Exit codes: 0 ok, 2 missing raster, 3 empty uncertainty, 4 payload, 5 claims/metrics,
6 CRS, 7 path-leak, 8 IO.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.partner_web import (  # noqa: E402
    EXIT_CLAIMS,
    EXIT_CRS,
    EXIT_EMPTY_UNCERTAINTY,
    EXIT_IO,
    EXIT_MISSING_RASTER,
    EXIT_OK,
    EXIT_PATH_LEAK,
    EXIT_PAYLOAD,
)
from src.partner_web.claims import (  # noqa: E402
    ClaimsError,
    default_input_paths,
    load_claims,
    resolve_metrics,
)
from src.partner_web.ethics_scan import EthicsError, scan_site_dir  # noqa: E402
from src.partner_web.html_site import HtmlError, write_site_html  # noqa: E402
from src.partner_web.pack import (  # noqa: E402
    PackError,
    copy_field_protocol,
    make_offline_zip,
    write_brief,
    write_brief_en,
    write_csv_template,
    write_deep_dives,
    write_email_template,
    write_whatsapp_strip,
)
from src.partner_web.render import (  # noqa: E402
    RenderError,
    build_layer_stack,
    enforce_payload_budget,
    write_layer_pngs,
)

# RenderError used in main() except block


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build partner web map + pack")
    p.add_argument("--claims", default=str(PROJECT_ROOT / "configs" / "claims.yaml"))
    p.add_argument("--wealth", default="")
    p.add_argument("--priority", default="")
    p.add_argument("--uncertainty", default="")
    p.add_argument("--metrics", default="")
    p.add_argument("--out-site", default=str(PROJECT_ROOT / "site"))
    p.add_argument("--out-pack", default=str(PROJECT_ROOT / "partner_pack"))
    p.add_argument("--max-edge", type=int, default=2048)
    p.add_argument("--max-overview-mb", type=float, default=12.0)
    p.add_argument("--fixtures", action="store_true", help="Use tests/fixtures rasters")
    p.add_argument("--skip-pack", action="store_true", help="PR1-style: site only")
    return p.parse_args()


def _git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    args = parse_args()
    claims_path = Path(args.claims)
    site_dir = Path(args.out_site)
    pack_dir = Path(args.out_pack)

    try:
        claims = load_claims(claims_path)
    except ClaimsError as exc:
        print(f"ERROR claims: {exc}", file=sys.stderr)
        return getattr(exc, "code", EXIT_CLAIMS)

    paths = default_input_paths(PROJECT_ROOT, claims)
    if args.fixtures:
        fix = PROJECT_ROOT / "tests" / "fixtures"
        paths["wealth"] = fix / "tiny_wealth.tif"
        paths["priority"] = fix / "tiny_priority.tif"
        paths["uncertainty"] = fix / "tiny_uncertainty.tif"
        paths["metrics"] = fix / "tiny_metrics.json"
    if args.wealth:
        paths["wealth"] = Path(args.wealth)
    if args.priority:
        paths["priority"] = Path(args.priority)
    if args.uncertainty:
        paths["uncertainty"] = Path(args.uncertainty)
    if args.metrics:
        paths["metrics"] = Path(args.metrics)

    # Prefer relative wealth path in manifest (avoid absolute host paths)
    wealth_disp = paths["wealth"]
    try:
        wealth_disp = wealth_disp.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        wealth_disp = Path(paths["wealth"].name)

    try:
        metrics = resolve_metrics(claims, paths["metrics"])
        stack = build_layer_stack(
            paths["wealth"],
            paths["priority"],
            paths["uncertainty"],
            max_edge=args.max_edge,
        )
        # Never store absolute machine paths in stack for ethics
        stack.wealth_path = wealth_disp.as_posix()

        assets = write_layer_pngs(stack, site_dir / "assets")
        leaflet_src = PROJECT_ROOT / "third_party" / "leaflet"
        write_site_html(
            site_dir,
            claims,
            metrics,
            stack.bounds_wgs84,
            leaflet_src=leaflet_src,
        )
        mb = enforce_payload_budget(site_dir, hard_mb=args.max_overview_mb)

        pack_meta: dict = {}
        if not args.skip_pack:
            write_brief(pack_dir, claims, metrics)
            write_brief_en(pack_dir, claims, metrics)
            write_deep_dives(pack_dir, assets, claims)
            write_email_template(pack_dir, claims)
            write_csv_template(pack_dir)
            copy_field_protocol(PROJECT_ROOT, pack_dir)
            write_whatsapp_strip(
                pack_dir,
                {
                    "wealth": stack.wealth,
                    "priority": stack.priority,
                    "uncertainty": stack.uncertainty,
                },
                claims,
            )
            zpath = pack_dir / "offline_bundle.zip"
            make_offline_zip(site_dir, pack_dir, zpath)
            pack_meta["offline_zip"] = "partner_pack/offline_bundle.zip"

        scan_site_dir(site_dir)

        manifest = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
            "wealth_path": stack.wealth_path,
            "wealth_units": claims.get("wealth_units"),
            "bounds_wgs84": stack.bounds_wgs84,
            "layer_shapes": stack.shapes,
            "assets_mb": round(mb, 3),
            "deep_dive_regions": ["Littoral", "Extreme-Nord"],
            "absolute_path_scan": "pass",
            "metrics": {k: metrics[k] for k in metrics if k not in ("artifacts",)},
            **pack_meta,
        }
        (site_dir / "build_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # re-scan after manifest
        scan_site_dir(site_dir)

    except ClaimsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "code", EXIT_CLAIMS)
    except RenderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exc.code
    except EthicsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "code", EXIT_PATH_LEAK)
    except (HtmlError, PackError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "code", EXIT_IO)
    except OSError as exc:
        print(f"ERROR IO: {exc}", file=sys.stderr)
        return EXIT_IO

    print(f"OK site={site_dir} pack={pack_dir if not args.skip_pack else '(skipped)'}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
