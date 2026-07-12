"""Tests modèle spatio-temporel."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.temporal.panel_model import (
    PANEL_YEARS,
    build_temporal_panel,
    compute_temporal_metrics,
    panel_to_geojson_records,
)

ROOT = Path(__file__).resolve().parents[1]


def test_build_temporal_panel_shape():
    clusters = gpd.read_parquet(ROOT / "data/processed/dhs_clusters_real.parquet")
    oof = pd.read_parquet(ROOT / "data/processed/training/oof_predictions.parquet")
    panel = build_temporal_panel(clusters, oof, project_root=ROOT)
    assert len(panel) == len(clusters) * len(PANEL_YEARS)
    assert set(panel["year"].unique()) == set(PANEL_YEARS)


def test_temporal_metrics_and_geojson():
    clusters = gpd.read_parquet(ROOT / "data/processed/dhs_clusters_real.parquet")
    oof = pd.read_parquet(ROOT / "data/processed/training/oof_predictions.parquet")
    panel = build_temporal_panel(clusters, oof, project_root=ROOT)
    metrics = compute_temporal_metrics(panel)
    assert metrics["n_clusters"] == len(clusters)
    assert "spearman_cluster_2018_vs_2022" in metrics
    geo = panel_to_geojson_records(panel)
    assert "2018" in geo
    assert len(geo["2018"]) == len(clusters)