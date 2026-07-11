#!/usr/bin/env python
"""
Régénère toutes les cartes et visualisations (modèle v4).

Usage :
  python scripts/make_maps.py
  python scripts/make_maps.py --with-inference   # inclut inférence raster v4
  python scripts/make_maps.py --v3               # legacy v3 uniquement
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Régénération des cartes")
    p.add_argument(
        "--with-inference",
        action="store_true",
        help="Lancer l'inférence nationale v4 avant les visualisations",
    )
    p.add_argument(
        "--v3",
        action="store_true",
        help="Utiliser le pipeline visualisations v3 (legacy)",
    )
    p.add_argument(
        "--skip-notebook",
        action="store_true",
        help="Ne pas exécuter le notebook 03",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.v3:
        script = "generate_results_visualizations.py"
        cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script)]
    else:
        script = "generate_results_v4_visualizations.py"
        cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script)]
        if not args.with_inference:
            cmd.append("--skip-inference")
        if args.skip_notebook:
            cmd.append("--skip-notebook-exec")

    print(f"▶ Cartes : {script}")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())