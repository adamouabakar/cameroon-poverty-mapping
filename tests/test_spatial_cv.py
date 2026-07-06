import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from src.utils.spatial_cv import (
    assign_spatial_blocks,
    block_based_cv,
    iter_cv_splits,
    select_cv_strategy,
    validate_fold_balance,
)


def _make_gdf(n: int = 50) -> gpd.GeoDataFrame:
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "cluster_id": range(1, n + 1),
            "wealth_index": rng.normal(size=n),
            "urban_rural": rng.choice(["urban", "rural"], size=n),
            "region": rng.choice(
                ["Centre", "Littoral", "Nord", "Est", "Ouest"], size=n
            ),
            "latitude": rng.uniform(2, 13, size=n),
            "longitude": rng.uniform(8, 16, size=n),
        }
    )
    geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def test_block_based_cv_no_overlap():
    gdf = _make_gdf()
    fold_ids = assign_spatial_blocks(gdf, n_folds=5)

    for train_idx, val_idx in iter_cv_splits(fold_ids, n_folds=5):
        assert len(set(train_idx) & set(val_idx)) == 0
        assert len(train_idx) + len(val_idx) == len(gdf)


def test_block_based_cv_yields_five_folds():
    gdf = _make_gdf()
    splits = list(block_based_cv(gdf, n_folds=5))
    assert len(splits) == 5


def test_select_cv_strategy_returns_valid_folds():
    gdf = _make_gdf()
    strategy, fold_ids, report = select_cv_strategy(gdf, preferred="auto", n_folds=5)
    assert strategy in {"block", "region"}
    assert len(fold_ids) == len(gdf)
    assert "is_balanced" in report


def test_validate_fold_balance_detects_small_validation():
    gdf = _make_gdf(n=12)
    fold_ids = pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1], name="fold_id")
    report = validate_fold_balance(gdf, fold_ids, min_val_size=5)
    assert report["is_balanced"] is False