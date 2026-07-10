import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from src.simulation.prioritization import (
    combine_normalized_components,
    compute_priority_index,
    normalize_component,
)


def _make_cluster_gdf(n: int = 20) -> gpd.GeoDataFrame:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "cluster_id": range(1, n + 1),
            "predicted_wealth": rng.uniform(-100000, 50000, n),
            "dist_school_km": rng.exponential(3.0, n),
            "dist_health_km": rng.exponential(4.0, n),
            "dist_road_km": rng.exponential(2.0, n),
        }
    )
    geometry = [Point(10 + i * 0.1, 4) for i in range(n)]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def test_normalize_component_invert():
    vals = np.array([0.0, 50.0, 100.0], dtype=np.float32)
    out = normalize_component(vals, 0.0, 100.0, invert=True)
    np.testing.assert_allclose(out, [1.0, 0.5, 0.0], rtol=1e-5)


def test_combine_normalized_components_weighted_mean():
    poverty = np.array([[1.0, 0.0]], dtype=np.float32)
    school = np.array([[0.0, 1.0]], dtype=np.float32)
    weights = {"poverty": 0.5, "dist_school": 0.5}
    out = combine_normalized_components(
        {"poverty": poverty, "dist_school": school}, weights
    )
    np.testing.assert_allclose(out, [[0.5, 0.5]], rtol=1e-5)


def test_compute_priority_index_vector():
    gdf = _make_cluster_gdf()
    result = compute_priority_index(gdf)
    assert "priority_index" in result.columns
    assert result["priority_index"].between(0, 1).all()


def test_poorer_cluster_can_rank_higher_with_same_access():
    gdf = gpd.GeoDataFrame(
        {
            "cluster_id": [1, 2],
            "predicted_wealth": [-50000.0, 50000.0],
            "dist_school_km": [5.0, 5.0],
            "dist_health_km": [5.0, 5.0],
            "dist_road_km": [5.0, 5.0],
        },
        geometry=[Point(10, 4), Point(11, 4)],
        crs="EPSG:4326",
    )
    ranked = compute_priority_index(gdf)
    poor = ranked.loc[ranked["cluster_id"] == 1, "priority_index"].iloc[0]
    rich = ranked.loc[ranked["cluster_id"] == 2, "priority_index"].iloc[0]
    assert poor > rich