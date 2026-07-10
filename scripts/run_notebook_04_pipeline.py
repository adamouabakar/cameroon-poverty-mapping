#!/usr/bin/env python
"""
Génère et exécute le Notebook 04 (inférence nationale + priorisation).

Usage :
  python scripts/run_notebook_04_pipeline.py
  python scripts/run_notebook_04_pipeline.py --build-only
  python scripts/run_notebook_04_pipeline.py --execute
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BUILD_SCRIPT = PROJECT_ROOT / "scripts/build_notebook_04.py"
NOTEBOOK = PROJECT_ROOT / "notebooks/04_national_inference_walkthrough.ipynb"
EXECUTED = PROJECT_ROOT / "notebooks/04_national_inference_walkthrough_executed.ipynb"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Notebook 04 pipeline")
    p.add_argument("--build-only", action="store_true", help="Générer le .ipynb uniquement")
    p.add_argument("--execute", action="store_true", help="Exécuter via nbclient après génération")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    subprocess.check_call([PYTHON, str(BUILD_SCRIPT)], cwd=PROJECT_ROOT)
    print(f"✅ Notebook généré : {NOTEBOOK}")

    if args.build_only:
        return 0

    if args.execute:
        import nbformat
        from nbclient import NotebookClient

        nb = nbformat.read(NOTEBOOK, as_version=4)
        client = NotebookClient(nb, timeout=600, kernel_name="python3")
        client.execute()
        nbformat.write(nb, EXECUTED)
        print(f"✅ Notebook exécuté : {EXECUTED}")
    else:
        print("ℹ️  Ouvrez le notebook dans Jupyter ou lancez avec --execute")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())