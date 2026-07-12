"""Tests v5_post feature engineering."""

from __future__ import annotations

import pandas as pd

from scripts.prepare_features_v5_post import build_v5_post_features


def test_build_v5_post_features():
    df = pd.DataFrame(
        {
            "precip_wet_season_mm": [800.0],
            "precip_annual_mm": [1600.0],
            "precip_cv": [0.2],
            "ndvi_mean": [0.5],
            "night_lights_mean": [10.0],
            "pop_density": [100.0],
            "ghsl_built_fraction": [0.3],
            "dist_road_km": [2.0],
            "dist_school_km": [4.0],
            "dist_health_km": [6.0],
        }
    )
    out = build_v5_post_features(df)
    assert "accessibility_inverse" in out.columns
    assert out["min_service_distance_km"].iloc[0] == 2.0
    assert out["ndvi_seasonality_proxy"].iloc[0] == 0.5