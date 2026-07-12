#!/usr/bin/env python
"""
Orchestrateur Post-v1.0 — Cameroon Poverty Mapping.

Usage :
  python scripts/run_post_v1.py --action 1
  python scripts/run_post_v1.py --action all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

ACTION_SCRIPTS = {
    1: "run_post_v1_action1_field_proxy.py",
    2: "run_post_v1_action2_ecam5.py",
    3: "run_post_v1_action3_model_v5.py",
    4: "run_post_v1_action4_maps.py",
    5: "run_post_v1_action5_publication.py",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exécute une action post-v1.0")
    p.add_argument("--action", required=True, help="1-5 ou 'all'")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "all":
        rc = 0
        for n in range(1, 6):
            rc |= _run_one(n)
        return rc
    return _run_one(int(args.action))


def _run_one(n: int) -> int:
    script = ACTION_SCRIPTS.get(n)
    if not script:
        print(f"❌ Action invalide : {n}")
        return 1
    path = PROJECT_ROOT / "scripts" / script
    if not path.exists():
        print(f"❌ Script introuvable : {path}")
        return 1
    print(f"\n{'='*60}\n▶ POST-V1 ACTION {n}\n{'='*60}")
    return subprocess.call([PYTHON, str(path)], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())