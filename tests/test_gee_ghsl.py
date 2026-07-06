"""Tests du composite GHSL (sans appel Earth Engine)."""

import pytest

from src.features.gee.config import load_gee_config, resolve_feature_set


def test_ghsl_config_present():
    config = load_gee_config("configs/gee.yaml")
    assert "ghsl" in config
    assert config["ghsl"]["collection"] == "JRC/GHSL/P2023A/GHS_BUILT_S"
    assert config["ghsl"]["epoch_year"] == 2015
    assert config["ghsl"]["band"] == "built_surface"


def test_ghsl_module_importable():
    from src.features.gee.composites.ghsl import get_ghsl_image, get_ghsl_raw_image

    assert callable(get_ghsl_image)
    assert callable(get_ghsl_raw_image)


def test_v2_band_mapping():
    config = load_gee_config("configs/gee.yaml")
    config_v2 = resolve_feature_set({**config, "feature_set": "v2"})
    assert config_v2["band_names"]["ghsl_built_fraction"] == "ghsl_built"


def test_v1_rejects_ghsl_column_in_active_set():
    config = load_gee_config("configs/gee.yaml")
    bad = resolve_feature_set({**config, "feature_set": "v1"})
    bad["feature_columns"] = bad["_base_feature_columns"][:-1] + ["ghsl_built_fraction"]
    bad["band_names"] = {**bad["_base_band_names"], "ghsl_built_fraction": "ghsl_built"}
    bad["band_names"].pop("built_density", None)
    from src.features.gee.config import validate_gee_config

    with pytest.raises(ValueError, match="réservé à feature_set v2"):
        validate_gee_config(bad)