#!/usr/bin/env python
"""Pipeline complet intégration INS : préparation → validation → features v4 → rapport."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline intégration INS")
    p.add_argument("--skip-v4", action="store_true", help="Ne pas générer le parquet features v4")
    return p.parse_args()


def _run(script: str) -> None:
    subprocess.check_call([PYTHON, str(PROJECT_ROOT / "scripts" / script)], cwd=PROJECT_ROOT)


def main() -> int:
    args = parse_args()
    steps: list[str] = []

    _run("prepare_ins_contextual_data.py")
    steps.append("prepare_ins_contextual_data")

    _run("run_ins_external_validation.py")
    steps.append("run_ins_external_validation")

    if not args.skip_v4:
        _run("merge_ins_features_v4.py")
        steps.append("merge_ins_features_v4")

    validation = json.loads(
        (PROJECT_ROOT / "outputs/reports/ins_external_validation.json").read_text(encoding="utf-8")
    )
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "INS Data Integration",
        "steps_completed": steps,
        "artifacts": {
            "ins_contextual": "data/processed/ins_contextual_data.parquet",
            "validation_report": "outputs/reports/ins_external_validation.json",
            "validation_table": "outputs/reports/ins_external_validation_table.csv",
            "validation_plot": "outputs/maps/ins_external_validation_scatter.png",
            "features_v4": None if args.skip_v4 else "data/processed/features/cluster_features_gee_ins_v4.parquet",
        },
        "key_metrics": validation.get("metrics", {}),
        "sources": validation.get("source_ins", {}),
        "limitations": [
            "Granularité régionale INS vs grappes/pixels DHS.",
            "ECAM 4 (2014) vs DHS 2018 — décalage temporel.",
            "Proxy richesse DHS ≠ pauvreté monétaire officielle.",
            "Douala/Yaoundé : proxy ECAM Littoral/Centre.",
        ],
        "recommendations": [
            "Phase 2 : ré-entraîner LightGBM sur feature set v4 et comparer OOF.",
            "Obtenir micro-données INS/ECAM via partenariat formel.",
            "Validation terrain sur sites à fort écart de rang.",
            "Raster v4 : zonal stats admin1 si limites officielles INS disponibles.",
        ],
    }

    out = PROJECT_ROOT / "outputs/reports/ins_integration_phase_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Pipeline INS terminé")
    print(f"  Rapport phase : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())