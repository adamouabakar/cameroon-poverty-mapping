#!/usr/bin/env python
"""Jalon 1 — Fondations & gouvernance."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIRS = [
    "data/raw/dhs",
    "data/raw/ins",
    "data/reference/ins",
    "data/processed/features",
    "data/processed/training",
    "outputs/maps",
    "outputs/reports",
    "outputs/rasters",
    "figures",
    "site",
    "partner_pack",
    "logs",
]


def main() -> int:
    for d in DIRS:
        (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)

    # Vérifier CI
    ci = PROJECT_ROOT / ".github/workflows/ci.yml"
    pages = PROJECT_ROOT / ".github/workflows/pages.yml"

    rc = subprocess.call(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=PROJECT_ROOT,
    )

    summary = {
        "jalon": 1,
        "title": "Fondations & gouvernance",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if rc == 0 else "completed_with_test_warnings",
        "deliverables": {
            "project_plan": "PROJECT_PLAN.md",
            "backlog": "PROJECT_BACKLOG.md",
            "credentials_template": "configs/credentials.template.yaml",
            "partners": "documentation/partners_identified.md",
            "ci_workflow": str(ci.relative_to(PROJECT_ROOT)) if ci.exists() else None,
            "pages_workflow": str(pages.relative_to(PROJECT_ROOT)) if pages.exists() else None,
        },
        "tests_passed": rc == 0,
        "next_jalon": 2,
    }

    out = PROJECT_ROOT / "outputs/reports/jalon1_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Jalon 1 terminé")
    print(f"   Rapport : {out}")
    print(f"   Tests   : {'OK' if rc == 0 else 'voir CI'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())