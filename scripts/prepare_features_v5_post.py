#!/usr/bin/env python
"""Feature set v5_post = ECAM5 base + séries temporelles proxy + accessibilité améliorée."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BASE_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_ins_ecam5.parquet"
OUT = PROJECT_ROOT / "data/processed/features/cluster_features_v5_post.parquet"

V5_POST_EXTRA = [
    "ndvi_seasonality_proxy",
    "ndvi_stability_index",
    "night_lights_per_capita",
    "built_night_trend_proxy",
    "accessibility_inverse",
    "min_service_distance_km",
    "road_access_score",
]


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.clip(lower=1e-6)


def build_v5_post_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    precip_cv = out["precip_cv"].clip(0, 2)
    out["ndvi_seasonality_proxy"] = _safe_ratio(out["precip_wet_season_mm"], out["precip_annual_mm"])
    out["ndvi_stability_index"] = out["ndvi_mean"] * (1.0 - precip_cv.clip(upper=1.0))
    out["night_lights_per_capita"] = out["night_lights_mean"] / np.log1p(out["pop_density"].clip(lower=0))
    out["built_night_trend_proxy"] = out["ghsl_built_fraction"] * out["night_lights_mean"]
    dist_mean = out[["dist_road_km", "dist_school_km", "dist_health_km"]].mean(axis=1)
    out["accessibility_inverse"] = 1.0 / (1.0 + dist_mean)
    out["min_service_distance_km"] = out[["dist_road_km", "dist_school_km", "dist_health_km"]].min(axis=1)
    out["road_access_score"] = 1.0 / (1.0 + out["dist_road_km"])
    return out


def main() -> int:
    if not BASE_PARQUET.is_file():
        raise SystemExit(f"Base ECAM5 features missing: {BASE_PARQUET}")
    df = pd.read_parquet(BASE_PARQUET)
    out = build_v5_post_features(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(f"✅ features v5_post : {OUT}")
    print(f"   Colonnes +{len(V5_POST_EXTRA)} : {V5_POST_EXTRA}")
    print(f"   Lignes : {len(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())