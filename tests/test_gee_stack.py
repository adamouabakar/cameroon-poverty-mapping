"""Tests de cohérence du stack GEE (sans appel Earth Engine)."""

import copy

import yaml

from src.features.gee.config import load_gee_config, resolve_feature_set
from src.features.gee.stack import QA_BANDS, get_model_bands, get_model_bands_legacy


def test_model_bands_match_config_active_set():
    config = load_gee_config("configs/gee.yaml")
    expected = list(config["band_names"].values())
    assert get_model_bands(config) == expected
    assert config["feature_set"] == "v2"
    assert "ghsl_built_fraction" in config["feature_columns"]


def test_model_bands_v1_legacy():
    config = load_gee_config("configs/gee.yaml")
    config_v1 = resolve_feature_set({**config, "feature_set": "v1"})
    assert get_model_bands(config_v1) == get_model_bands_legacy()
    assert "built_density" in config_v1["feature_columns"]


def test_model_bands_v2_uses_ghsl():
    config = load_gee_config("configs/gee.yaml")
    config_v2 = resolve_feature_set({**config, "feature_set": "v2"})
    bands = get_model_bands(config_v2)
    assert bands[-1] == "ghsl_built"
    assert "ghsl_built_fraction" in config_v2["feature_columns"]
    assert "built_density" not in config_v2["feature_columns"]


def test_qa_bands_are_documented():
    assert QA_BANDS == ["ndwi", "evi"]


def test_feature_columns_count_active_set():
    config = load_gee_config("configs/gee.yaml")
    assert len(config["feature_columns"]) == 10
    assert len(config["band_names"]) == 10
    assert "ghsl_built_fraction" in config["feature_columns"]


def test_feature_columns_count_v2_from_yaml():
    with open("configs/gee.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    config_v2 = resolve_feature_set({**raw["gee"], "feature_set": "v2"})
    assert len(config_v2["feature_columns"]) == 10
    assert config_v2["band_names"]["ghsl_built_fraction"] == "ghsl_built"


def test_model_bands_v3_includes_chirps():
    config = load_gee_config("configs/gee.yaml")
    config_v3 = resolve_feature_set({**config, "feature_set": "v3"})
    bands = get_model_bands(config_v3)
    assert len(bands) == 13
    assert bands[-3:] == ["precip_annual", "precip_wet", "precip_cv"]
    assert "precip_annual_mm" in config_v3["feature_columns"]