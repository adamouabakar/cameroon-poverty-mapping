#!/usr/bin/env python
"""Jalon 3 — Features avancées v5."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/run_model_v5_evaluation.py")],
        cwd=PROJECT_ROOT,
    )
    summary = {
        "jalon": 3,
        "status": "completed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "deliverables": {
            "features_v5": "data/processed/features/cluster_features_v5.parquet",
            "report": "outputs/reports/model_v5_results.json",
        },
        "next_jalon": 4,
    }
    out = PROJECT_ROOT / "outputs/reports/jalon3_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("✅ Jalon 3 terminé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())