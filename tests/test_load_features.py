from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from src.data.load_dhs import load_dhs_clusters
from src.features.load_features import load_cluster_features, resolve_feature_source
from src.utils.config import load_config


@pytest.fixture
def config():
    return load_config("configs/default.yaml")


@pytest.fixture
def gdf():
    return load_dhs_clusters(use_fake=True)


def test_resolve_feature_source_fake(config):
    config["features"]["fake"] = True
    config["features"]["source"] = "fake"
    assert resolve_feature_source(config) == "fake"


def test_resolve_feature_source_gee_flag(config):
    config["features"]["fake"] = False
    assert resolve_feature_source(config) == "gee"


def test_resolve_feature_source_gee_explicit(config):
    config["features"]["fake"] = True
    config["features"]["source"] = "gee"
    assert resolve_feature_source(config) == "gee"


def test_load_cluster_features_fake(gdf, config):
    config["features"]["fake"] = True
    config["features"]["source"] = "fake"
    features_df, source = load_cluster_features(gdf, config)
    assert source == "fake"
    assert len(features_df) == len(gdf)
    assert "night_lights_mean" in features_df.columns


def test_load_cluster_features_gee_from_parquet(gdf, config, tmp_path):
    config["features"]["fake"] = False
    config["features"]["source"] = "gee"
    cols = config["features"]["columns"]
    df = pd.DataFrame(
        {
            "cluster_id": gdf["cluster_id"].values,
            **{c: 1.0 for c in cols},
        }
    )
    parquet_path = tmp_path / "cluster_features_gee.parquet"
    df.to_parquet(parquet_path, index=False)
    config["features"]["gee_parquet"] = "cluster_features_gee.parquet"

    features_df, source = load_cluster_features(gdf, config, project_root=tmp_path)
    assert source == "gee"
    assert list(features_df.columns) == ["cluster_id", *cols]