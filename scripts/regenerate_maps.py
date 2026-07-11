#!/usr/bin/env python
"""Alias — régénère cartes v4 (voir scripts/make_maps.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    rc = subprocess.call(
        [sys.executable, str(PROJECT_ROOT / "scripts/make_maps.py"), "--skip-notebook"],
        cwd=PROJECT_ROOT,
    )
    raise SystemExit(rc)