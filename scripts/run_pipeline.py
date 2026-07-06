#!/usr/bin/env python
"""
Pipeline complet — Cartographie de la pauvreté au Cameroun (DHS 2018 + GEE v3).

Étapes :
  1. Préparation grappes DHS réelles (si fichiers bruts présents)
  2. Extraction features GEE v3 (si compte Earth Engine configuré)
  3. Entraînement + évaluation LightGBM
  4. Visualisations et cartes

Usage :
  python scripts/run_pipeline.py                    # tout (si données présentes)
  python scripts/run_pipeline.py --skip-gee         # modèle + cartes seulement
  python scripts/run_pipeline.py --skip-dhs         # GEE + modèle (clusters déjà prêts)
  python scripts/run_pipeline.py --only maps        # régénérer cartes uniquement

Prérequis :
  - Python 3.10+, pip install -r requirements.txt
  - Données DHS dans data/raw/dhs/ (CMGE + CMHR)
  - earthengine authenticate (pour extraction GEE)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def _run(script: str, *args: str, step: str) -> int:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n{'='*60}\n▶ {step}\n   {' '.join(cmd)}\n{'='*60}")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline complet Cameroon Poverty Mapping")
    p.add_argument("--skip-dhs", action="store_true", help="Ignorer préparation DHS")
    p.add_argument("--skip-gee", action="store_true", help="Ignorer extraction GEE")
    p.add_argument("--skip-model", action="store_true", help="Ignorer entraînement")
    p.add_argument("--skip-maps", action="store_true", help="Ignorer visualisations")
    p.add_argument(
        "--only",
        choices=["dhs", "gee", "model", "maps"],
        help="Exécuter une seule étape",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    steps = {"dhs": True, "gee": True, "model": True, "maps": True}

    if args.only:
        steps = {k: (k == args.only) for k in steps}
    if args.skip_dhs:
        steps["dhs"] = False
    if args.skip_gee:
        steps["gee"] = False
    if args.skip_model:
        steps["model"] = False
    if args.skip_maps:
        steps["maps"] = False

    rc = 0
    if steps["dhs"]:
        rc |= _run("prepare_real_dhs_clusters.py", step="1/4 — Préparation DHS")
    if steps["gee"]:
        rc |= _run(
            "extract_gee_features.py",
            "--mode", "clusters",
            "--feature-set", "v3",
            "--clusters", "data/processed/dhs_clusters_real.parquet",
            "--output", "data/processed/features/cluster_features_gee_real.parquet",
            step="2/4 — Extraction GEE v3",
        )
    if steps["model"]:
        rc |= _run(
            "run_real_model_evaluation.py",
            "--skip-notebook",
            step="3/4 — Modélisation + évaluation",
        )
    if steps["maps"]:
        rc |= _run("generate_results_visualizations.py", step="4/4 — Visualisations")

    print("\n" + ("✅ Pipeline terminé" if rc == 0 else f"⚠️ Pipeline terminé avec erreurs (code {rc})"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())