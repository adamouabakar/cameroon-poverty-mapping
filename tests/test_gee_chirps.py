"""Tests du composite CHIRPS (sans appel Earth Engine)."""

import pytest

from src.features.gee.composites.chirps import (
    CHIRPS_FEATURE_COLUMNS,
    get_chirps_composite,
    uses_chirps_features,
)
from src.features.gee.config import load_gee_config, resolve_feature_set, validate_gee_config


def test_chirps_config_present():
    config = load_gee_config("configs/gee.yaml")
    assert "chirps" in config
    assert config["chirps"]["collection"] == "UCSB-CHG/CHIRPS/DAILY"
    assert config["chirps"]["start"] == "2018-01-01"
    assert config["chirps"]["end"] == "2018-12-31"
    assert config["chirps"]["wet_season_start_month"] == 3
    assert config["chirps"]["wet_season_end_month"] == 11


def test_chirps_module_importable():
    from src.features.gee.composites.chirps import get_chirps_collection

    assert callable(get_chirps_collection)
    assert callable(get_chirps_composite)


def test_v3_band_mapping():
    config = load_gee_config("configs/gee.yaml")
    config_v3 = resolve_feature_set({**config, "feature_set": "v3"})
    assert config_v3["band_names"]["precip_annual_mm"] == "precip_annual"
    assert config_v3["band_names"]["precip_wet_season_mm"] == "precip_wet"
    assert config_v3["band_names"]["precip_cv"] == "precip_cv"


def test_v3_requires_all_chirps_columns():
    config = load_gee_config("configs/gee.yaml")
    bad = resolve_feature_set({**config, "feature_set": "v3"})
    bad["feature_columns"] = [
        col for col in bad["feature_columns"] if col != "precip_cv"
    ]
    with pytest.raises(ValueError, match="colonnes CHIRPS"):
        validate_gee_config(bad)


def test_v2_rejects_chirps_columns():
    config = load_gee_config("configs/gee.yaml")
    bad = resolve_feature_set({**config, "feature_set": "v2"})
    bad["feature_columns"] = list(bad["feature_columns"]) + ["precip_annual_mm"]
    bad["band_names"] = {**bad["band_names"], "precip_annual_mm": "precip_annual"}
    with pytest.raises(ValueError, match="réservées à feature_set v3"):
        validate_gee_config(bad)


def test_uses_chirps_features():
    config = load_gee_config("configs/gee.yaml")
    config_v2 = resolve_feature_set({**config, "feature_set": "v2"})
    config_v3 = resolve_feature_set({**config, "feature_set": "v3"})
    assert not uses_chirps_features(config_v2)
    assert uses_chirps_features(config_v3)
    assert CHIRPS_FEATURE_COLUMNS == frozenset({
        "precip_annual_mm",
        "precip_wet_season_mm",
        "precip_cv",
    })