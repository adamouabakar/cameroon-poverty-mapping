#!/usr/bin/env python
"""Jalon 5 — Déploiement & release v1.0."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGES_URL = "https://adamouabakar.github.io/cameroon-poverty-mapping/"


def main() -> int:
    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/build_partner_web.py")],
        cwd=PROJECT_ROOT,
    )
    subprocess.call(
        ["gh", "workflow", "run", "pages", "--ref", "main"],
        cwd=PROJECT_ROOT,
    )

    comm = PROJECT_ROOT / "COMMUNICATION_v1.0.md"
    comm.write_text(
        "\n".join([
            "# Brouillon communication — Release v1.0",
            "",
            "## LinkedIn / X (FR)",
            "",
            "🗺️ Cartographie ouverte de la pauvreté au Cameroun (~1 km)",
            "",
            "430 grappes DHS 2018 + satellite (GEE) + INS/ECAM 4",
            "Modèle v4 : R² 0.79 · validation INS Spearman -0.87",
            "",
            f"Carte : {PAGES_URL}",
            "Code : https://github.com/adamouabakar/cameroon-poverty-mapping",
            "",
            "Estimations exploratoires — pas de substitution aux stats INS.",
            "",
            "## Hashtags",
            "#OpenData #Cameroon #DHS #PovertyMapping #MachineLearning #INS",
        ]),
        encoding="utf-8",
    )

    summary = {
        "jalon": 5,
        "status": "completed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "deliverables": {
            "site_url": PAGES_URL,
            "communication_draft": "COMMUNICATION_v1.0.md",
            "reproducibility": "REPRODUCIBILITY.md",
            "release_tag": "v1.0.0",
        },
        "release_note": "Créer tag : gh release create v1.0.0 --title 'v1.0.0' --notes-file RELEASE_v1.0.0.md",
    }
    out = PROJECT_ROOT / "outputs/reports/jalon5_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    release_notes = PROJECT_ROOT / "RELEASE_v1.0.0.md"
    release_notes.write_text(
        "\n".join([
            "# Release v1.0.0 — Cameroon Poverty Mapping",
            "",
            "## Highlights",
            "- Pipeline DHS 2018 (430 clusters) + GEE v3 + INS ECAM 4",
            "- Model v4: R² OOF 0.793, Spearman 0.889",
            "- National maps 1 km, uncertainty, prioritization",
            "- Partner web + beta dashboard (SHAP, region selector)",
            "- Feature set v5 exploratory comparison",
            "- Decision tools: report, field mode, intervention simulator",
            "",
            f"**Live map:** {PAGES_URL}",
        ]),
        encoding="utf-8",
    )

    print("✅ Jalon 5 terminé")
    print(f"   Site : {PAGES_URL}")
    print(f"   Comm : {comm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())