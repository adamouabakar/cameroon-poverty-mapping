"""Tests configuration et logique VIIRS (sans appel Earth Engine)."""

import yaml

from src.features.gee.composites.viirs import _quality_clear_values


def test_viirs_config_uses_nasa_002():
    with open("configs/gee.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["gee"]["viirs"]
    assert cfg["collection"] == "NASA/VIIRS/002/VNP46A2"
    assert cfg["band"] == "Gap_Filled_DNB_BRDF_Corrected_NTL"
    assert cfg["quality_clear_values"] == [0, 1]


def test_quality_clear_values_from_list():
    cfg = {"quality_clear_values": [0, 1]}
    assert _quality_clear_values(cfg) == [0, 1]


def test_quality_clear_values_legacy_single():
    cfg = {"quality_clear_value": 0}
    assert _quality_clear_values(cfg) == [0]