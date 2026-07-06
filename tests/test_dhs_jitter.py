import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.data.jitter import (
    EXTENDED_FRACTION,
    EXTENDED_JITTER_KM,
    RURAL_JITTER_KM,
    URBAN_JITTER_KM,
    simulate_dhs_jitter,
    validate_buffer_covers_jitter,
)


def _sample_clusters(n: int = 20) -> gpd.GeoDataFrame:
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "cluster_id": range(1, n + 1),
        "urban_rural": ["urban"] * (n // 2) + ["rural"] * (n - n // 2),
        "latitude": rng.uniform(3, 12, size=n),
        "longitude": rng.uniform(9, 15, size=n),
    })
    geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def test_jitter_moves_points_but_stays_within_max_radius():
    gdf = _sample_clusters(50)
    original = gdf.copy()
    jittered = simulate_dhs_jitter(gdf, random_state=42)

    assert "jitter_distance_km" in jittered.columns
    assert "jitter_extended" in jittered.columns
    assert not jittered.geometry.equals(original.geometry)

    max_allowed = np.where(
        jittered["jitter_extended"],
        EXTENDED_JITTER_KM,
        np.where(
            jittered["urban_rural"] == "urban",
            URBAN_JITTER_KM,
            RURAL_JITTER_KM,
        ),
    )
    assert (jittered["jitter_distance_km"] <= max_allowed + 1e-9).all()


def test_jitter_reproducible_with_same_seed():
    gdf1 = _sample_clusters(10)
    gdf2 = _sample_clusters(10)
    out1 = simulate_dhs_jitter(gdf1, random_state=123)
    out2 = simulate_dhs_jitter(gdf2, random_state=123)
    pd.testing.assert_series_equal(out1["latitude"], out2["latitude"])
    pd.testing.assert_series_equal(out1["longitude"], out2["longitude"])


def test_extended_fraction_approx_one_percent():
    gdf = _sample_clusters(2000)
    jittered = simulate_dhs_jitter(gdf, random_state=7)
    frac = jittered["jitter_extended"].mean()
    assert 0.003 < frac < 0.02


def test_validate_buffer_covers_jitter_passes():
    buffer_km = pd.Series([2.0, 5.0, 5.0])
    jitter_km = pd.Series([1.5, 4.0, 3.0])
    validate_buffer_covers_jitter(buffer_km, jitter_km)


def test_validate_buffer_covers_jitter_raises():
    buffer_km = pd.Series([2.0, 5.0])
    jitter_km = pd.Series([2.5, 4.0])
    with pytest.raises(ValueError, match="buffer plus petit"):
        validate_buffer_covers_jitter(buffer_km, jitter_km)