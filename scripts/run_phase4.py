#!/usr/bin/env python
"""
Phase 4 — Profils partenaires, packs de livraison, déploiement cloud Streamlit.

Usage:
  python scripts/run_phase4.py
  python scripts/run_phase4.py --partner nord_humanitaire
  python scripts/run_phase4.py --skip-tests
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
PYTHON = sys.executable


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 4 — livraison partenaires & cloud")
    p.add_argument("--partner", default=None, help="Un seul partenaire (sinon --all)")
    p.add_argument("--skip-tests", action="store_true")
    p.add_argument("--skip-deliveries", action="store_true")
    return p.parse_args()


def _run(cmd: list[str]) -> None:
    print(f"▶ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def _write_manifest(deliveries: list[dict]) -> Path:
    manifest = {
        "phase": 4,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "partner_profiles": "configs/partners/",
        "deliveries": deliveries,
        "streamlit_cloud": {
            "entrypoint": "streamlit_demo.py",
            "config": ".streamlit/config.toml",
            "docker": "docker-compose.yml",
        },
        "features": [
            "multi_partner_profiles",
            "partner_delivery_zip",
            "streamlit_partner_selector",
            "admin_boundaries_overlay",
            "streamlit_cloud_config",
        ],
    }
    out = PROJECT_ROOT / "outputs/reports/phase4_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Manifeste Phase 4 : {out}")
    return out


def main() -> int:
    from src.reports.partner_delivery import build_partner_delivery
    from src.reports.partner_profile import list_partner_profiles, load_partner_profile

    args = parse_args()
    print("=== Phase 4 — Livraison partenaires & cloud ===\n")

    delivery_records: list[dict] = []

    if not args.skip_deliveries:
        if args.partner:
            profiles = [load_partner_profile(PROJECT_ROOT, args.partner)]
        else:
            profiles = list_partner_profiles(PROJECT_ROOT)

        for profile in profiles:
            zip_path = build_partner_delivery(PROJECT_ROOT, profile)
            delivery_records.append(
                {
                    "partner_id": profile.partner_id,
                    "display_name": profile.display_name,
                    "focus_region": profile.focus_region,
                    "zip": str(zip_path.relative_to(PROJECT_ROOT)),
                }
            )
            print(f"✅ Pack : {zip_path}")

    if not args.skip_tests:
        _run(
            [
                PYTHON,
                "-m",
                "pytest",
                "tests/test_partner_profile.py",
                "tests/test_partner_delivery.py",
                "tests/test_report_config.py",
                "tests/test_pdf_report.py",
                "-q",
            ]
        )

    _write_manifest(delivery_records)

    print("\n=== Phase 4 terminée ===")
    print("  Profils : configs/partners/*.yaml")
    print("  Livraisons : partner_pack/deliveries/")
    print("  Streamlit Cloud : pointer vers streamlit_demo.py + .streamlit/config.toml")
    print("  Docker : docker compose up streamlit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())