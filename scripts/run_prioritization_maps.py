#!/usr/bin/env python
"""
Phase 2 — cartes de priorisation spatiale.

Combine la carte wealth raster (Sprint 1) et les distances OSM du stack GEE
pour produire un indice composite exploratoire.

Usage :
  python scripts/run_prioritization_maps.py
  python scripts/run_prioritization_maps.py --wealth outputs/maps/wealth_index_predicted_1km_model.tif
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

WEALTH_DEFAULT = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model.tif"
FEATURES_DEFAULT = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
CRITERIA_DEFAULT = PROJECT_ROOT / "configs/prioritization_criteria.yaml"


def _cluster_priority_report(top_n: int = 30) -> list[dict]:
    """Top zones prioritaires au niveau grappe (complément au raster)."""
    import geopandas as gpd
    import pandas as pd

    from src.simulation.prioritization import compute_priority_index, load_prioritization_config
    from src.simulation.ranking import get_top_priority_zones

    clusters = gpd.read_parquet(PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet")
    oof = pd.read_parquet(PROJECT_ROOT / "data/processed/training/oof_predictions.parquet")
    features = pd.read_parquet(
        PROJECT_ROOT / "data/processed/features/cluster_features_gee_real.parquet"
    )

    merged = clusters.merge(oof[["cluster_id", "y_oof_pred"]], on="cluster_id", how="inner")
    merged = merged.merge(features, on="cluster_id", how="inner", suffixes=("", "_feat"))
    merged["predicted_wealth"] = merged["y_oof_pred"]

    criteria = load_prioritization_config(CRITERIA_DEFAULT)
    ranked = compute_priority_index(merged, weights=criteria["weights"])
    top = get_top_priority_zones(ranked, top_n=top_n)

    rows = []
    for _, row in top.iterrows():
        rows.append({
            "cluster_id": int(row["cluster_id"]),
            "region": row.get("region"),
            "priority_index": round(float(row["priority_index"]), 4),
            "predicted_wealth": round(float(row["predicted_wealth"]), 2),
            "dist_school_km": round(float(row.get("dist_school_km", 0)), 2),
            "dist_health_km": round(float(row.get("dist_health_km", 0)), 2),
            "dist_road_km": round(float(row.get("dist_road_km", 0)), 2),
        })
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cartes de priorisation Phase 2")
    p.add_argument("--wealth", default=str(WEALTH_DEFAULT))
    p.add_argument("--features", default=str(FEATURES_DEFAULT))
    p.add_argument("--criteria", default=str(CRITERIA_DEFAULT))
    p.add_argument("--top-n", type=int, default=30)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    wealth_path = PROJECT_ROOT / args.wealth
    features_path = PROJECT_ROOT / args.features
    criteria_path = PROJECT_ROOT / args.criteria

    for path, label in [
        (wealth_path, "wealth raster"),
        (features_path, "features raster"),
        (criteria_path, "criteria"),
    ]:
        if not path.exists():
            print(f"❌ {label} introuvable : {path}")
            return 1

    from src.simulation.prioritization import load_prioritization_config
    from src.simulation.priority_raster import compute_priority_raster
    from src.visualization.static_maps import plot_raster_preview

    criteria = load_prioritization_config(criteria_path)
    out_cfg = criteria.get("output", {})
    priority_tif = PROJECT_ROOT / out_cfg.get(
        "priority_raster", "outputs/maps/priority_index_1km.tif"
    )
    priority_png = PROJECT_ROOT / out_cfg.get(
        "priority_preview", "outputs/maps/priority_index_1km.png"
    )
    report_path = PROJECT_ROOT / out_cfg.get(
        "report", "outputs/reports/prioritization_results.json"
    )

    print("▶ Calcul indice de priorisation raster…")
    compute_priority_raster(
        wealth_path, features_path, criteria_path, priority_tif
    )

    plot_raster_preview(
        priority_tif,
        priority_png,
        title="Indice de priorisation composite (1 km) — Phase 2",
        cmap="YlOrRd",
    )

    print("▶ Top grappes prioritaires…")
    top_clusters = _cluster_priority_report(top_n=args.top_n)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "prioritization",
        "weights": criteria["weights"],
        "inputs": {
            "wealth_raster": str(wealth_path),
            "features_raster": str(features_path),
        },
        "outputs": {
            "priority_raster": str(priority_tif),
            "priority_preview": str(priority_png),
        },
        "top_clusters": top_clusters,
        "note": "Indice exploratoire — validation locale requise avant usage opérationnel.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("✅ Priorisation Phase 2 terminée")
    print(f"   Raster : {priority_tif}")
    print(f"   Aperçu : {priority_png}")
    print(f"   Rapport : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())