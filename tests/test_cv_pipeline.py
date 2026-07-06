import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from src.data.load_dhs import load_dhs_clusters
from src.data.merge_features import merge_dhs_with_features
from src.data.prepare_labels import create_cluster_buffers
from src.features.generate_fake_features import FAKE_FEATURE_COLUMNS, generate_fake_geospatial_features
from src.models.cv_pipeline import run_spatial_cv
from src.models.evaluate import build_cv_report, compute_metrics, compute_spearman
from src.models.uncertainty import attach_prediction_intervals, compute_residual_uncertainty
from src.utils.config import load_config


@pytest.fixture
def training_setup():
    config = load_config("configs/default.yaml")
    gdf = load_dhs_clusters(use_fake=True)
    gdf = create_cluster_buffers(gdf)
    features = generate_fake_geospatial_features(gdf, random_state=42)
    df = merge_dhs_with_features(gdf, features)
    X = df[FAKE_FEATURE_COLUMNS]
    y = df["wealth_index"]
    return config, gdf, X, y, df


def test_fake_features_count_and_columns(training_setup):
    _, gdf, _, _, _ = training_setup
    features = generate_fake_geospatial_features(gdf, random_state=42)
    assert features.shape[1] == 11
    assert list(features.columns[1:]) == FAKE_FEATURE_COLUMNS


def test_run_spatial_cv_produces_oof_predictions(training_setup):
    config, gdf, X, y, _ = training_setup
    cv_results = run_spatial_cv(X, y, gdf, config, return_models=True)

    assert cv_results.oof_predictions.notna().all()
    assert len(cv_results.fold_metrics) == config["model"]["n_folds"]
    assert len(cv_results.best_iterations) == config["model"]["n_folds"]
    assert cv_results.cv_strategy in {"block", "region"}


def test_global_oof_metrics_are_finite(training_setup):
    config, gdf, X, y, _ = training_setup
    cv_results = run_spatial_cv(X, y, gdf, config, return_models=False)

    metrics = compute_metrics(y, cv_results.oof_predictions)
    metrics["spearman"] = compute_spearman(y, cv_results.oof_predictions)

    assert np.isfinite(metrics["r2"])
    assert np.isfinite(metrics["rmse"])
    assert np.isfinite(metrics["mae"])
    assert np.isfinite(metrics["spearman"])


def test_uncertainty_intervals(training_setup):
    config, gdf, X, y, df = training_setup
    cv_results = run_spatial_cv(X, y, gdf, config, return_models=False)
    uncertainty = compute_residual_uncertainty(cv_results.oof_residuals)
    oof_df = attach_prediction_intervals(
        cv_results.oof_predictions,
        y,
        uncertainty,
        meta=df[["cluster_id", "region", "urban_rural"]],
    )

    assert "lower_90" in oof_df.columns
    assert "upper_90" in oof_df.columns
    assert len(oof_df) == len(y)
    assert uncertainty["method"] == "global_residual_quantile_oof"