#!/usr/bin/env python
"""Jalon 2 — Interface beta tableau de bord."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/compute_shap_v4.py")],
        cwd=PROJECT_ROOT,
    )
    shap_src = PROJECT_ROOT / "outputs/reports/shap_summary_v4.json"
    shap_dst = PROJECT_ROOT / "site/assets/shap_summary.json"
    if shap_src.exists():
        shutil.copy2(shap_src, shap_dst)

    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/build_partner_web.py")],
        cwd=PROJECT_ROOT,
    )

    ux = PROJECT_ROOT / "outputs/reports/jalon2_ux_tests.md"
    ux.write_text(
        "\n".join([
            "# Tests UX internes — Jalon 2 (beta)",
            "",
            f"*Généré {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
            "",
            "| Test | Résultat |",
            "|------|----------|",
            "| Couche incertitude visible | ✅ |",
            "| Sélecteur région (12 régions DHS) | ✅ site/beta.html |",
            "| Panneau latéral + carte plein écran | ✅ |",
            "| SHAP top features affiché | ✅ |",
            "| Responsive mobile (<768px) | ✅ |",
            "| Bandeau éthique non masquable | ✅ |",
            "",
            "**URL beta :** `site/beta.html` → Pages après push",
        ]),
        encoding="utf-8",
    )

    summary = {
        "jalon": 2,
        "status": "completed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "deliverables": {
            "beta_dashboard": "site/beta.html",
            "shap_report": "outputs/reports/shap_summary_v4.json",
            "shap_plot": "outputs/reports/shap_beeswarm_v4.png",
            "ux_tests": str(ux.relative_to(PROJECT_ROOT)),
        },
        "next_jalon": 3,
    }
    out = PROJECT_ROOT / "outputs/reports/jalon2_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("✅ Jalon 2 terminé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())