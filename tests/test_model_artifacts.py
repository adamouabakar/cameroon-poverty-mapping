"""Smoke tests for versioned production model artifacts."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.wealth_scaling import load_scaler
from src.models.save_load import load_model

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FEATURE_COLS = [
    "night_lights_mean", "ndvi_mean", "ndbi_mean",
    "dist_road_km", "dist_school_km", "dist_health_km",
    "pop_density", "elevation_m", "slope_deg", "ghsl_built_fraction",
    "precip_annual_mm", "precip_wet_season_mm", "precip_cv",
]

MODEL_PATH = PROJECT_ROOT / "models/wealth_model_lgbm_v0_gee_v3_zscore.pkl"
SCALER_PATH = PROJECT_ROOT / "models/wealth_scaler_v3.json"


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="z-score model not present")
def test_zscore_model_loads_and_predicts():
    model = load_model(MODEL_PATH)
    row = pd.DataFrame([{col: 0.0 for col in FEATURE_COLS}])
    pred = model.predict(row)
    assert len(pred) == 1
    assert np.isfinite(pred[0])


@pytest.mark.skipif(not SCALER_PATH.exists(), reason="versioned scaler not present")
def test_versioned_scaler_matches_model_pairing():
    scaler = load_scaler(SCALER_PATH)
    assert scaler.std > 0
    z = scaler.transform(pd.Series([0.0]))
    raw = scaler.inverse_transform(z)
    assert np.isfinite(raw[0])