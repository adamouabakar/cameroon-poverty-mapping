#!/usr/bin/env python
"""
Extraction de features GEE pour le pipeline Cameroon Poverty Mapping.

Usage:
  python scripts/extract_gee_features.py --dry-run
  python scripts/extract_gee_features.py --mode test
  python scripts/extract_gee_features.py --mode clusters --clusters data/processed/dhs_prepared_with_buffers.parquet
  python scripts/extract_gee_features.py --mode national --destination asset
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.gee.client import initialize_gee
from src.features.gee.config import load_gee_config, resolve_feature_set
from src.features.gee.export_raster import launch_national_export
from src.features.gee.extract_clusters import (
    _filter_clusters_to_test_bbox,
    extract_from_clusters_file,
)
from src.features.gee.qa import validate_features
from src.features.gee.stack import build_feature_image, get_model_bands
from src.features.gee.aoi import get_aoi_geometry
from src.utils.helpers import get_project_root, hash_config_file

import geopandas as gpd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extraction features GEE")
    parser.add_argument(
        "--mode",
        choices=["test", "clusters", "national"],
        default="test",
        help="test=zone Yaoundé ; clusters=toutes grappes ; national=export raster",
    )
    parser.add_argument(
        "--clusters",
        default="data/processed/dhs_prepared_with_buffers.parquet",
        help="Chemin vers les grappes/buffers DHS",
    )
    parser.add_argument(
        "--output",
        default="data/processed/features/cluster_features_gee.parquet",
        help="Sortie parquet (modes test/clusters)",
    )
    parser.add_argument(
        "--destination",
        choices=["asset", "drive"],
        default="asset",
        help="Destination export national",
    )
    parser.add_argument(
        "--gee-config",
        default=None,
        help="Chemin vers configs/gee.yaml",
    )
    parser.add_argument(
        "--feature-set",
        choices=["v1", "v2", "v3"],
        default=None,
        help="Surcharge feature_set (ex. v3 = GHSL + CHIRPS)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valide la config et affiche le résumé sans appeler Earth Engine",
    )
    return parser.parse_args()


def _build_extraction_report(
    *,
    config: dict,
    clusters_path: Path,
    output_path: Path,
    features_df,
    qa_report: dict,
    elapsed_seconds: float,
    aoi_label: str | None = None,
    issues: list[str] | None = None,
) -> dict:
    """Rapport QA structuré pour une extraction clusters."""
    feature_cols = config["feature_columns"]
    missing_rates = {
        col: float(features_df[col].isna().mean()) if col in features_df.columns else 1.0
        for col in feature_cols
    }
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_set": config.get("feature_set"),
        "n_clusters_input": int(gpd.read_parquet(clusters_path).shape[0]) if clusters_path.exists() else None,
        "n_clusters_extracted": len(features_df),
        "success_rate": round(len(features_df) / max(1, gpd.read_parquet(clusters_path).shape[0]), 4),
        "feature_columns": feature_cols,
        "gee_bands": get_model_bands(config),
        "missing_rates": missing_rates,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "elapsed_minutes": round(elapsed_seconds / 60, 2),
        "output_path": str(output_path),
        "clusters_path": str(clusters_path),
        "aoi_used": aoi_label,
        "qa_passed": qa_report.get("passed", False),
        "qa_checks": qa_report.get("checks", []),
        "issues": issues or [],
    }


def _dry_run_summary(
    config: dict,
    mode: str,
    clusters_path: Path,
) -> dict:
    """Résumé local (pas d'appel GEE) pour vérifier la config avant extraction."""
    clusters_gdf = gpd.read_parquet(clusters_path)
    if mode == "test":
        clusters_gdf = _filter_clusters_to_test_bbox(clusters_gdf, config)

    return {
        "mode": mode,
        "project_id": config.get("project_id"),
        "crs": config["crs"],
        "export_scale": config["export_scale"],
        "test_bbox": config["test_aoi"]["bbox"],
        "n_clusters": len(clusters_gdf),
        "feature_columns": config["feature_columns"],
        "gee_bands": get_model_bands(config),
        "qa_bands": ["ndwi", "evi"],
    }


def main() -> None:
    args = parse_args()
    root = get_project_root()
    gee_config_path = Path(args.gee_config) if args.gee_config else root / "configs" / "gee.yaml"
    config = load_gee_config(gee_config_path)
    feature_set = args.feature_set or ("v3" if args.mode == "national" else None)
    if feature_set:
        config = resolve_feature_set({**config, "feature_set": feature_set})
    clusters_path = root / args.clusters
    output_path = root / args.output
    qa_report_path = root / "outputs/reports/gee_extraction_real_qa.json"

    log = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "config_hash": hash_config_file(gee_config_path),
        "destination": args.destination if args.mode == "national" else None,
    }

    if args.dry_run:
        dry_mode = "clusters" if args.mode == "clusters" else ("test" if args.mode == "test" else "national")
        summary = _dry_run_summary(
            config=config,
            mode=dry_mode,
            clusters_path=clusters_path,
        )
        log["dry_run"] = True
        log["summary"] = summary
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if not summary["project_id"]:
            print(
                "\n⚠️  gee.project_id est null — définissez-le dans configs/gee.yaml "
                "avant l'extraction réelle."
            )
        print("\nDry-run OK. Lancez sans --dry-run après : earthengine authenticate")
    elif args.mode == "national":
        initialize_gee(project_id=config.get("project_id"))
        aoi = get_aoi_geometry(config, mode="national")
        image = build_feature_image(aoi, config)
        task = launch_national_export(image, config, destination=args.destination)
        status = task.status()
        export_name = config.get("export", {}).get("national_asset_name", "cm_features_1km_v3")
        export_report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "feature_set": config.get("feature_set"),
            "task_id": task.id,
            "state": status.get("state"),
            "destination": args.destination,
            "asset_id": f"{config['export']['asset_prefix']}/{export_name}",
            "scale_m": config["export_scale"],
            "crs": config["crs"],
            "bands": get_model_bands(config),
        }
        report_path = root / "outputs/reports/gee_national_export.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(export_report, indent=2), encoding="utf-8")
        log["task_id"] = task.id
        log["status"] = status.get("state")
        log["export_report"] = str(report_path)
        print(f"Export national lancé : task.id={task.id}")
        print(f"Rapport export : {report_path}")
    else:
        import time

        initialize_gee(project_id=config.get("project_id"))
        mode = "test" if args.mode == "test" else "clusters"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        issues: list[str] = []
        t0 = time.perf_counter()
        try:
            features_df = extract_from_clusters_file(
                clusters_path=clusters_path,
                config=config,
                mode=mode,
            )
        except Exception as exc:
            issues.append(f"extraction_failed: {exc}")
            raise
        elapsed = time.perf_counter() - t0

        qa_report = validate_features(features_df, config["feature_columns"])
        features_df.to_parquet(output_path, index=False)

        aoi_label = getattr(features_df, "attrs", {}).get("aoi_used")
        extraction_report = _build_extraction_report(
            config=config,
            clusters_path=clusters_path,
            output_path=output_path,
            features_df=features_df,
            qa_report=qa_report,
            elapsed_seconds=elapsed,
            aoi_label=aoi_label,
            issues=issues,
        )
        qa_report_path.parent.mkdir(parents=True, exist_ok=True)
        qa_report_path.write_text(
            json.dumps(extraction_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        log["n_clusters"] = len(features_df)
        log["output"] = str(output_path)
        log["qa"] = qa_report
        log["elapsed_seconds"] = extraction_report["elapsed_seconds"]
        log["extraction_report"] = str(qa_report_path)
        print(f"Features extraites : {len(features_df)} grappes → {output_path}")
        print(f"Durée : {extraction_report['elapsed_minutes']:.1f} min")
        print(f"Rapport QA : {qa_report_path}")
        if not qa_report["passed"]:
            print("⚠️  QA : certains contrôles de plage sont hors limites (voir log).")
            issues.append("qa_range_warnings")

    logs_dir = root / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f"gee_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Journal : {log_path}")


if __name__ == "__main__":
    main()