#!/usr/bin/env python
"""
Pipeline complet — Cartographie de la pauvreté au Cameroun (DHS 2018 + GEE v3 + INS v4).

Étapes :
  1. Préparation grappes DHS réelles
  2. Extraction features GEE v3 (clusters)
  3. Intégration INS (ECAM 4) + features v4
  4. Entraînement + évaluation LightGBM v4
  5. Inférence nationale raster v4 + visualisations

Usage :
  python scripts/run_pipeline.py
  python scripts/run_pipeline.py --skip-gee --skip-dhs
  python scripts/run_pipeline.py --only maps
  python scripts/run_pipeline.py --v3          # pipeline legacy v3

Prérequis :
  - Python 3.10+, pip install -r requirements.txt
  - Données DHS dans data/raw/dhs/ (CMGE + CMHR)
  - earthengine authenticate (pour extraction GEE)
  - Raster national GEE pour inférence : data/processed/rasters/cm_features_1km_v3.tif
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

FEATURES_RASTER = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"


def _run(script: str, *args: str, step: str) -> int:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n{'='*60}\n▶ {step}\n   {' '.join(cmd)}\n{'='*60}")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline complet Cameroon Poverty Mapping")
    p.add_argument("--skip-dhs", action="store_true", help="Ignorer préparation DHS")
    p.add_argument("--skip-gee", action="store_true", help="Ignorer extraction GEE")
    p.add_argument("--skip-ins", action="store_true", help="Ignorer intégration INS")
    p.add_argument("--skip-model", action="store_true", help="Ignorer entraînement")
    p.add_argument("--skip-inference", action="store_true", help="Ignorer inférence raster v4")
    p.add_argument("--skip-maps", action="store_true", help="Ignorer visualisations")
    p.add_argument(
        "--only",
        choices=["dhs", "gee", "ins", "model", "inference", "maps"],
        help="Exécuter une seule étape",
    )
    p.add_argument(
        "--v3",
        action="store_true",
        help="Pipeline legacy v3 (sans INS ni modèle v4)",
    )
    return p.parse_args()


def _run_v3_pipeline(args: argparse.Namespace) -> int:
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
            step="3/4 — Modélisation v3",
        )
    if steps["maps"]:
        rc |= _run("generate_results_visualizations.py", step="4/4 — Visualisations v3")
    return rc


def _run_v4_pipeline(args: argparse.Namespace) -> int:
    steps = {
        "dhs": True,
        "gee": True,
        "ins": True,
        "model": True,
        "inference": True,
        "maps": True,
    }
    if args.only:
        steps = {k: (k == args.only) for k in steps}
    if args.skip_dhs:
        steps["dhs"] = False
    if args.skip_gee:
        steps["gee"] = False
    if args.skip_ins:
        steps["ins"] = False
    if args.skip_model:
        steps["model"] = False
    if args.skip_inference:
        steps["inference"] = False
    if args.skip_maps:
        steps["maps"] = False

    rc = 0
    if steps["dhs"]:
        rc |= _run("prepare_real_dhs_clusters.py", step="1/6 — Préparation DHS")
    if steps["gee"]:
        rc |= _run(
            "extract_gee_features.py",
            "--mode", "clusters",
            "--feature-set", "v3",
            "--clusters", "data/processed/dhs_clusters_real.parquet",
            "--output", "data/processed/features/cluster_features_gee_real.parquet",
            step="2/6 — Extraction GEE v3 (base clusters)",
        )
    if steps["ins"]:
        rc |= _run("run_ins_integration_pipeline.py", step="3/6 — Intégration INS + features v4")
    if steps["model"]:
        rc |= _run(
            "run_model_v4_evaluation.py",
            "--skip-notebook",
            step="4/6 — Modélisation v4 (GEE + INS)",
        )
    if steps["inference"]:
        if FEATURES_RASTER.exists():
            rc |= _run("run_national_inference_v4.py", step="5/6 — Inférence nationale v4")
        else:
            print(
                f"\n⚠️  Raster GEE absent : {FEATURES_RASTER}\n"
                "   Saut inférence raster — téléchargez via download_gee_raster_local.py"
            )
    if steps["maps"]:
        map_args: list[str] = []
        if steps["inference"] and FEATURES_RASTER.exists():
            map_args = ["--skip-inference"]
        elif args.skip_inference:
            map_args = ["--skip-inference"]
        rc |= _run(
            "generate_results_v4_visualizations.py",
            *map_args,
            step="6/6 — Visualisations v4",
        )
    return rc


def main() -> int:
    args = parse_args()
    rc = _run_v3_pipeline(args) if args.v3 else _run_v4_pipeline(args)
    print("\n" + ("✅ Pipeline terminé" if rc == 0 else f"⚠️ Pipeline terminé avec erreurs (code {rc})"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())