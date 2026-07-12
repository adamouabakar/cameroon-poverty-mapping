"""Tests statistiques régionales."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.reports.region_stats import (
    compute_regional_summary,
    filter_clusters_by_region,
    load_cluster_frame,
)

ROOT = Path(__file__).resolve().parents[1]


def test_load_and_filter_clusters():
    df = load_cluster_frame(ROOT)
    assert len(df) == 430
    sub = filter_clusters_by_region(df, "Extrême-Nord")
    assert sub["region"].nunique() <= 1
    assert len(sub) >= 1


def test_regional_summary_national():
    df = load_cluster_frame(ROOT)
    summary = compute_regional_summary(df)
    assert "Tout le Cameroun" in summary["region"].values
    assert len(summary) >= 12


def test_regional_summary_single():
    df = load_cluster_frame(ROOT)
    summary = compute_regional_summary(df, region="Centre")
    assert len(summary) == 1
    assert summary.iloc[0]["region"] == "Centre"