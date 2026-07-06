import pandas as pd
import pytest

from src.features.gee.config import load_gee_config
from src.features.gee.postprocess import features_to_model_schema
from src.features.gee.qa import validate_features


@pytest.fixture
def gee_config():
    return load_gee_config("configs/gee.yaml")


def test_features_to_model_schema(gee_config):
    raw = pd.DataFrame(
        {
            "cluster_id": [1, 2],
            "night_lights": [1.5, 2.0],
            "ndvi": [0.4, 0.5],
            "ndbi": [0.1, 0.2],
            "dist_road_m": [1000, 2000],
            "dist_school_m": [500, 1500],
            "dist_health_m": [800, 1800],
            "pop_density": [100, 200],
            "elevation": [700, 800],
            "slope": [2.0, 3.0],
            "ghsl_built": [0.2, 0.3],
        }
    )
    out = features_to_model_schema(raw, gee_config)
    assert list(out.columns) == ["cluster_id"] + gee_config["feature_columns"]
    assert out.loc[0, "dist_road_km"] == 1.0
    assert out.loc[1, "dist_school_km"] == 1.5


def test_validate_features_pass(gee_config):
    df = pd.DataFrame(
        {
            "cluster_id": [1],
            "night_lights_mean": [1.0],
            "ndvi_mean": [0.5],
            "ndbi_mean": [0.1],
            "dist_road_km": [1.0],
            "dist_school_km": [2.0],
            "dist_health_km": [3.0],
            "pop_density": [100.0],
            "elevation_m": [500.0],
            "slope_deg": [5.0],
            "ghsl_built_fraction": [0.2],
        }
    )
    report = validate_features(df, gee_config["feature_columns"])
    assert report["passed"] is True