from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from src.data.load_dhs import has_real_dhs_files, load_dhs_clusters


def test_load_fake_clusters_default_schema():
    gdf = load_dhs_clusters(use_fake=True, apply_jitter=True, random_state=42)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert gdf.crs.to_epsg() == 4326
    assert len(gdf) == 50
    for col in ("cluster_id", "wealth_index", "urban_rural", "region", "latitude", "longitude"):
        assert col in gdf.columns
    assert gdf["wealth_index"].isna().sum() == 0
    assert set(gdf["urban_rural"].unique()) <= {"urban", "rural"}


def test_fake_clusters_without_jitter_differs_from_with_jitter():
    raw = load_dhs_clusters(use_fake=True, apply_jitter=False, random_state=1)
    jittered = load_dhs_clusters(use_fake=True, apply_jitter=True, random_state=1)
    assert not np.allclose(raw["latitude"], jittered["latitude"])


def test_real_mode_requires_jitter(tmp_path):
    gps = pd.DataFrame({
        "DHSCLUST": [1, 2],
        "LATNUM": [4.0, 5.0],
        "LONGNUM": [9.0, 10.0],
        "URBAN_RURA": ["U", "R"],
        "DHSREGNA": ["Centre", "Littoral"],
    })
    hr = pd.DataFrame({
        "hv001": [1, 1, 2, 2],
        "hv271": [0.5, 0.7, -0.2, -0.1],
    })
    gps.to_stata(tmp_path / "CMGE7FL.dta", write_index=False)
    hr.to_stata(tmp_path / "CMHR7FL.dta", write_index=False)

    assert has_real_dhs_files(tmp_path)

    gdf = load_dhs_clusters(tmp_path, use_fake=False, apply_jitter=True, random_state=0)
    assert len(gdf) == 2
    assert "jitter_distance_km" in gdf.columns
    assert "latitude_raw" not in gdf.columns
    assert "longitude_raw" not in gdf.columns
    assert gdf.loc[gdf["cluster_id"] == 1, "wealth_index"].iloc[0] == pytest.approx(0.6)


def test_real_mode_rejects_no_jitter(tmp_path):
    gps = pd.DataFrame({
        "DHSCLUST": [1],
        "LATNUM": [4.0],
        "LONGNUM": [9.0],
        "URBAN_RURA": ["U"],
        "DHSREGNA": ["Centre"],
    })
    hr = pd.DataFrame({"hv001": [1], "hv271": [0.5]})
    gps.to_stata(tmp_path / "CMGE7FL.dta", write_index=False)
    hr.to_stata(tmp_path / "CMHR7FL.dta", write_index=False)

    with pytest.raises(ValueError, match="Coordonnées GPS non déplacées"):
        load_dhs_clusters(tmp_path, use_fake=False, apply_jitter=False)


def test_auto_detect_fake_when_no_files(tmp_path):
    gdf = load_dhs_clusters(tmp_path, use_fake=None)
    assert len(gdf) == 50