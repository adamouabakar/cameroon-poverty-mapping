#!/usr/bin/env python
"""
Orchestrateur des 5 jalons — Cameroon Poverty Mapping.

Usage :
  python scripts/run_jalon.py --jalon 1
  python scripts/run_jalon.py --jalon all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

JALON_SCRIPTS = {
    1: "run_jalon1_fondations.py",
    2: "run_jalon2_interface.py",
    3: "run_jalon3_features.py",
    4: "run_jalon4_fonctionnalites.py",
    5: "run_jalon5_deploiement.py",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exécute un jalon du planning")
    p.add_argument("--jalon", required=True, help="1-5 ou 'all'")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.jalon == "all":
        rc = 0
        for n in range(1, 6):
            rc |= _run_one(n)
        return rc
    return _run_one(int(args.jalon))


def _run_one(n: int) -> int:
    script = JALON_SCRIPTS.get(n)
    if not script:
        print(f"❌ Jalon invalide : {n}")
        return 1
    path = PROJECT_ROOT / "scripts" / script
    if not path.exists():
        print(f"❌ Script introuvable : {path}")
        return 1
    print(f"\n{'='*60}\n▶ JALON {n}\n{'='*60}")
    return subprocess.call([PYTHON, str(path)], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())