import pytest

from src.features.gee.config import (
    get_crs,
    get_feature_set,
    get_scale,
    get_test_bbox,
    load_gee_config,
    resolve_feature_set,
    validate_gee_config,
)


def test_load_gee_config():
    config = load_gee_config("configs/gee.yaml")
    assert config["crs"] == "EPSG:32633"
    assert config["export_scale"] == 1000


def test_get_helpers():
    config = load_gee_config("configs/gee.yaml")
    assert get_scale(config) == 1000
    assert get_crs(config) == "EPSG:32633"
    assert len(get_test_bbox(config)) == 4


def test_validate_rejects_missing_key():
    with pytest.raises(ValueError, match="Clés manquantes"):
        validate_gee_config({"export_scale": 1000})


def test_feature_set_active_is_v2():
    config = load_gee_config("configs/gee.yaml")
    assert get_feature_set(config) == "v2"


def test_resolve_feature_set_v2_swaps_built_column():
    config = load_gee_config("configs/gee.yaml")
    config_v2 = resolve_feature_set({**config, "feature_set": "v2"})
    assert "ghsl_built_fraction" in config_v2["feature_columns"]
    assert "built_density" not in config_v2["feature_columns"]


def test_resolve_feature_set_v3_adds_chirps():
    config = load_gee_config("configs/gee.yaml")
    config_v3 = resolve_feature_set({**config, "feature_set": "v3"})
    assert len(config_v3["feature_columns"]) == 13
    assert "precip_annual_mm" in config_v3["feature_columns"]
    assert "precip_wet_season_mm" in config_v3["feature_columns"]
    assert "precip_cv" in config_v3["feature_columns"]