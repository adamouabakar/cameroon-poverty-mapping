#!/usr/bin/env python
"""
Inférence nationale de l'indice de richesse (~1 km).

Modes :
  interpolate  — grille IDW depuis prédictions OOF des 430 grappes (immédiat)
  raster       — inférence pixel à pixel depuis GeoTIFF features GEE exporté

Usage :
  python scripts/run_national_inference.py --mode interpolate
  python scripts/run_national_inference.py --mode raster --features data/processed/rasters/cm_features_1km_v3.tif
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MAPS_DIR = PROJECT_ROOT / "outputs/maps"
CLUSTERS_PATH = PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet"
OOF_PATH = PROJECT_ROOT / "data/processed/training/oof_predictions.parquet"
MODEL_PATH = PROJECT_ROOT / "models/wealth_model_lgbm_v0_gee_v3.pkl"
MODEL_ZSCORE_PATH = PROJECT_ROOT / "models/wealth_model_lgbm_v0_gee_v3_zscore.pkl"
SCALER_VERSIONED_PATH = PROJECT_ROOT / "models/wealth_scaler_v3.json"
SCALER_LOCAL_PATH = PROJECT_ROOT / "data/processed/training/wealth_scaler.json"


def resolve_scaler_path() -> Path | None:
    if SCALER_VERSIONED_PATH.exists():
        return SCALER_VERSIONED_PATH
    if SCALER_LOCAL_PATH.exists():
        return SCALER_LOCAL_PATH
    return None


def run_interpolate() -> dict:
    import geopandas as gpd

    from src.visualization.static_maps import (
        export_interpolated_raster,
        merge_oof_with_clusters,
        plot_raster_preview,
    )

    clusters = gpd.read_parquet(CLUSTERS_PATH)
    oof = __import__("pandas").read_parquet(OOF_PATH)
    gdf = merge_oof_with_clusters(clusters, oof)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    wealth_tif = MAPS_DIR / "wealth_index_predicted_1km.tif"
    unc_tif = MAPS_DIR / "wealth_uncertainty_1km.tif"

    export_interpolated_raster(gdf, "y_oof_pred", wealth_tif)
    export_interpolated_raster(gdf, "uncertainty_half_width", unc_tif)

    plot_raster_preview(
        wealth_tif,
        MAPS_DIR / "wealth_index_predicted_1km.png",
        title="Carte nationale — wealth index estimé (OOF interpolé, 1 km)",
    )
    plot_raster_preview(
        unc_tif,
        MAPS_DIR / "wealth_uncertainty_1km.png",
        title="Carte nationale — incertitude (demi-largeur intervalle 90 %)",
        cmap="Purples",
    )

    return {
        "mode": "interpolate",
        "wealth_raster": str(wealth_tif),
        "uncertainty_raster": str(unc_tif),
        "note": "Interpolation RBF depuis 430 grappes — pas une inférence pixel GEE directe.",
    }


def run_raster(features_path: Path) -> dict:
    from src.features.gee.config import load_gee_config, resolve_feature_set
    from src.models.predict_raster import predict_wealth_raster
    from src.visualization.static_maps import plot_raster_preview

    config = resolve_feature_set({**load_gee_config(), "feature_set": "v3"})
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    scaler_path = resolve_scaler_path()
    use_zscore = MODEL_ZSCORE_PATH.exists() and scaler_path is not None
    if MODEL_ZSCORE_PATH.exists() and scaler_path is None:
        print(
            "⚠️  Modèle z-score présent mais scaler absent — "
            "fallback sur wealth_model_lgbm_v0_gee_v3.pkl. "
            "Lancez scripts/sprint1_standardized_evaluation.py."
        )
    model_path = MODEL_ZSCORE_PATH if use_zscore else MODEL_PATH
    out_z = MAPS_DIR / "wealth_index_predicted_1km_model_z.tif"
    out_raw = MAPS_DIR / "wealth_index_predicted_1km_model.tif"

    predict_wealth_raster(
        features_path,
        model_path,
        out_z if use_zscore else out_raw,
        config,
        scaler_path=scaler_path if use_zscore else None,
        output_raw_path=out_raw if use_zscore else None,
    )
    preview_path = out_raw if out_raw.exists() else out_z
    plot_raster_preview(
        preview_path,
        MAPS_DIR / "wealth_index_predicted_1km_model.png",
        title="Inférence modèle sur grille GEE 1 km (raster direct)",
    )
    return {
        "mode": "raster",
        "model": str(model_path),
        "wealth_raster_z": str(out_z) if use_zscore else None,
        "wealth_raster_raw": str(out_raw),
        "features_raster": str(features_path),
        "note": "Inférence pixel à pixel depuis stack GEE exporté — pas interpolation RBF.",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inférence nationale wealth index")
    p.add_argument("--mode", choices=["interpolate", "raster"], default="interpolate")
    p.add_argument("--features", default=None, help="GeoTIFF features v3 (mode raster)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "raster":
        if not args.features:
            print("❌ --features requis en mode raster")
            return 1
        result = run_raster(PROJECT_ROOT / args.features)
    else:
        result = run_interpolate()
    print("✅ Inférence nationale terminée")
    for k, v in result.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())