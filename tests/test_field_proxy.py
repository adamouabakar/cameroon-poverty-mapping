"""Tests for proxy field validation helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from src.validation.field_proxy import (
    local_assessment_from_bins,
    concordance_from_assessment,
    select_stratified_clusters,
    wealth_series_to_bins,
)


def test_local_assessment_from_bins():
    assert local_assessment_from_bins("bas", "haut") == "plus pauvre"
    assert local_assessment_from_bins("haut", "bas") == "plus aisé"
    assert local_assessment_from_bins("moyen", "moyen") == "similaire"


def test_concordance_from_assessment():
    assert concordance_from_assessment("similaire", "moyen") == "match"
    assert concordance_from_assessment("plus pauvre", "bas") == "match"
    assert concordance_from_assessment("plus pauvre", "haut") == "mismatch"


def test_wealth_series_to_bins():
    s = pd.Series([-3.0, 0.0, 3.0, 6.0])
    bins = wealth_series_to_bins(s)
    assert set(bins.unique()) <= {"bas", "moyen", "haut"}


def test_select_stratified_clusters():
    df = pd.DataFrame(
        {
            "cluster_id": range(1, 13),
            "latitude": [4.0] * 12,
            "longitude": [9.0] * 12,
            "region": ["A"] * 4 + ["B"] * 4 + ["C"] * 4,
            "wealth_index": range(12),
            "urban_rural": ["urban", "rural"] * 6,
        }
    )
    out = select_stratified_clusters(df, min_per_region=1, seed=1)
    assert out["region"].nunique() == 3
    assert len(out) >= 3