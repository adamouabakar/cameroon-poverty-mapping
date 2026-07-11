#!/usr/bin/env python
"""Jalon 4 — Outils décisionnels."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.intervention_simulator import demo_scenarios, simulate_intervention  # noqa: E402


def main() -> int:
    subprocess = __import__("subprocess")
    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/generate_decision_report.py")],
        cwd=PROJECT_ROOT,
    )

    v5_path = PROJECT_ROOT / "data/processed/features/cluster_features_v5.parquet"
    if not v5_path.exists():
        subprocess.check_call(
            [sys.executable, str(PROJECT_ROOT / "scripts/prepare_features_v5.py")],
            cwd=PROJECT_ROOT,
        )
    df = pd.read_parquet(v5_path).head(50)
    sim_rows = []
    for sc in demo_scenarios():
        sim = simulate_intervention(df, sc)
        sim_rows.append({
            "scenario": sc.name,
            "mean_delta_wealth": float(sim["simulated_wealth_delta"].mean()),
            "n_clusters": len(sim),
        })

    sim_out = PROJECT_ROOT / "outputs/reports/intervention_simulator_v0.json"
    sim_out.write_text(json.dumps(sim_rows, indent=2), encoding="utf-8")

    summary = {
        "jalon": 4,
        "status": "completed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "deliverables": {
            "decision_report": "outputs/reports/decision_report.html",
            "field_mode": "site/field.html",
            "simulator": "src/simulation/intervention_simulator.py",
            "simulator_demo": str(sim_out.relative_to(PROJECT_ROOT)),
        },
        "next_jalon": 5,
    }
    out = PROJECT_ROOT / "outputs/reports/jalon4_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("✅ Jalon 4 terminé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())