#!/usr/bin/env python
"""
Sprint 1 — Crédibilité technique.

Étapes :
  1. Évaluation wealth z-score
  2. Dry-run / lancement export GEE national v3
  3. Inférence raster (si GeoTIFF features présent)
  4. Rapport sprint + instructions release v0.1.0

Usage :
  python scripts/sprint1_launch.py                    # tout sauf GEE réel
  python scripts/sprint1_launch.py --launch-gee       # lance export national GEE
  python scripts/sprint1_launch.py --launch-gee-test    # export AOI test → Drive
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

FEATURES_NATIONAL = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
FEATURES_TEST = PROJECT_ROOT / "data/processed/rasters/cm_features_test_1km_v3.tif"
SPRINT_REPORT = PROJECT_ROOT / "outputs/reports/sprint1_status.json"


def _run(script: str, *args: str, step: str) -> tuple[int, str]:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n{'='*60}\n▶ {step}\n   {' '.join(cmd)}\n{'='*60}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def _launch_gee_export(*, test_only: bool, destination: str) -> dict:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.features.gee.aoi import get_aoi_geometry
    from src.features.gee.client import initialize_gee
    from src.features.gee.config import load_gee_config, resolve_feature_set
    from src.features.gee.export_raster import launch_national_export
    from src.features.gee.stack import build_feature_image

    config = resolve_feature_set({**load_gee_config(), "feature_set": "v3"})
    initialize_gee(project_id=config.get("project_id"))

    if test_only:
        aoi = get_aoi_geometry(config, mode="test")
        desc = "cm_features_test_1km_v3"
    else:
        aoi = get_aoi_geometry(config, mode="national")
        desc = config["export"].get("national_asset_name", "cm_features_1km_v3")

    image = build_feature_image(aoi, config)
    task = launch_national_export(
        image, config, destination=destination, aoi=aoi, description=desc
    )
    status = task.status()
    return {
        "task_id": task.id,
        "state": status.get("state"),
        "description": desc,
        "destination": destination,
        "test_only": test_only,
        "asset_or_drive": (
            f"{config['export']['asset_prefix']}/{desc}"
            if destination == "asset"
            else config["export"]["drive_folder"]
        ),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sprint 1 — pipeline national")
    p.add_argument("--launch-gee", action="store_true", help="Lancer export GEE national (asset)")
    p.add_argument(
        "--launch-gee-test",
        action="store_true",
        help="Lancer export GEE sur AOI test (Drive, plus rapide)",
    )
    p.add_argument(
        "--gee-destination",
        choices=["asset", "drive"],
        default="drive",
        help="Destination export national (défaut: drive — plus fiable sans asset folder)",
    )
    p.add_argument("--skip-zscore", action="store_true")
    p.add_argument("--skip-raster", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    report: dict = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 1,
        "steps": {},
    }
    errors: list[str] = []

    if not args.skip_zscore:
        code, out = _run("sprint1_standardized_evaluation.py", step="1/4 Évaluation z-score")
        report["steps"]["zscore_evaluation"] = {"exit_code": code}
        if code != 0:
            errors.append("zscore_evaluation")

    gee_info = None
    if args.launch_gee or args.launch_gee_test:
        try:
            gee_info = _launch_gee_export(
                test_only=args.launch_gee_test,
                destination="drive" if args.launch_gee_test else args.gee_destination,
            )
            print(f"\n✅ Export GEE lancé : {gee_info}")
            report["steps"]["gee_export"] = gee_info
            export_report = PROJECT_ROOT / "outputs/reports/gee_national_export.json"
            export_report.parent.mkdir(parents=True, exist_ok=True)
            export_report.write_text(
                json.dumps(gee_info, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            errors.append(f"gee_export: {exc}")
            report["steps"]["gee_export"] = {"error": str(exc)}
    else:
        code, out = _run(
            "extract_gee_features.py",
            "--mode", "national",
            "--feature-set", "v3",
            "--dry-run",
            step="2/4 Dry-run export GEE national v3",
        )
        report["steps"]["gee_dry_run"] = {"exit_code": code}
        if code != 0:
            errors.append("gee_dry_run")

    if not args.skip_raster:
        features_path = None
        if FEATURES_NATIONAL.exists():
            features_path = FEATURES_NATIONAL
        elif FEATURES_TEST.exists():
            features_path = FEATURES_TEST

        if features_path:
            code, _ = _run(
                "run_national_inference.py",
                "--mode", "raster",
                "--features", str(features_path.relative_to(PROJECT_ROOT)),
                step="3/4 Inférence raster directe",
            )
            report["steps"]["raster_inference"] = {
                "exit_code": code,
                "features": str(features_path),
            }
            if code != 0:
                errors.append("raster_inference")
        else:
            msg = (
                "GeoTIFF features absent — placez le fichier sous "
                f"{FEATURES_NATIONAL} après export GEE, ou lancez --launch-gee-test."
            )
            print(f"\n⚠️  {msg}")
            report["steps"]["raster_inference"] = {"skipped": msg}

    report["release"] = {
        "version": "v0.1.0",
        "tag_command": "git tag -a v0.1.0 -m \"Sprint 1: z-score, GEE national v3, raster inference\"",
        "push_command": "git push origin v0.1.0",
    }
    report["errors"] = errors
    report["success"] = len(errors) == 0

    SPRINT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SPRINT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Rapport sprint 1 : {SPRINT_REPORT}")
    if errors:
        print(f"⚠️  Étapes en erreur : {', '.join(errors)}")
        return 1
    print("✅ Sprint 1 terminé (voir rapport pour étapes async GEE)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())