#!/usr/bin/env python
"""Régénère cartes et figures à partir des résultats existants."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    rc = subprocess.call(
        [sys.executable, str(PROJECT_ROOT / "scripts/generate_results_visualizations.py")],
        cwd=PROJECT_ROOT,
    )
    raise SystemExit(rc)