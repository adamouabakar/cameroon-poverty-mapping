#!/usr/bin/env python
"""
Phase 3 — Rapport ONG configurable, ECAM5 dashboard, watchlist, déploiement Streamlit.

Usage:
  python scripts/run_phase3.py
  python scripts/run_phase3.py --lang en
  python scripts/run_phase3.py --skip-tests
  python scripts/run_phase3.py --docker-build
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
    p = argparse.ArgumentParser(description="Phase 3 — outils ONG avancés")
    p.add_argument("--lang", choices=["fr", "en"], default="fr")
    p.add_argument("--region", default="Tout le Cameroun")
    p.add_argument("--skip-tests", action="store_true")
    p.add_argument("--skip-pdf", action="store_true")
    p.add_argument("--skip-geojson", action="store_true")
    p.add_argument("--docker-build", action="store_true", help="Construire l'image Streamlit")
    return p.parse_args()


def _run(cmd: list[str], *, cwd: Path = PROJECT_ROOT) -> None:
    print(f"▶ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def _write_admin_geojson() -> Path | None:
    from src.reports.admin_boundaries import write_dhs_region_geojson

    out = PROJECT_ROOT / "data/reference/admin/dhs_regions_bounds.geojson"
    try:
        write_dhs_region_geojson(out)
        print(f"✅ GeoJSON admin : {out}")
        return out
    except Exception as exc:
        print(f"⚠ GeoJSON admin ignoré : {exc}")
        return None


def _write_phase3_manifest(lang: str, pdf_path: Path) -> Path:
    manifest = {
        "phase": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "language": lang,
        "pdf_report": str(pdf_path.relative_to(PROJECT_ROOT)),
        "config": "configs/ngo_report.yaml",
        "streamlit": "streamlit_demo.py",
        "docker": {"compose": "docker-compose.yml", "image": "cameroon-poverty-streamlit"},
        "features": [
            "configurable_pdf_fr_en",
            "ecam5_model_comparison",
            "regional_watchlist_alerts",
            "field_validation_csv",
            "streamlit_docker",
        ],
    }
    out = PROJECT_ROOT / "outputs/reports/phase3_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"✅ Manifeste Phase 3 : {out}")
    return out


def main() -> int:
    args = parse_args()
    print("=== Phase 3 — Outils ONG avancés ===\n")

    if not args.skip_geojson:
        _write_admin_geojson()

    pdf_out = PROJECT_ROOT / f"outputs/reports/ngo_report_phase3_{args.lang}.pdf"
    if not args.skip_pdf:
        _run(
            [
                PYTHON,
                "scripts/generate_ngo_pdf_report.py",
                "--lang",
                args.lang,
                "--region",
                args.region,
                "--output",
                str(pdf_out.relative_to(PROJECT_ROOT)),
            ]
        )

    if not args.skip_tests:
        _run(
            [
                PYTHON,
                "-m",
                "pytest",
                "tests/test_report_config.py",
                "tests/test_watchlist.py",
                "tests/test_ecam5_dashboard.py",
                "tests/test_pdf_report.py",
                "tests/test_region_stats.py",
                "-q",
            ]
        )

    _write_phase3_manifest(args.lang, pdf_out)

    if args.docker_build:
        _run(["docker", "compose", "build", "streamlit"])

    print("\n=== Phase 3 terminée ===")
    print("  PDF :", pdf_out)
    print("  Streamlit : streamlit run streamlit_demo.py")
    print("  Docker : docker compose up streamlit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())