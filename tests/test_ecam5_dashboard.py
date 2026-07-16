"""Tests comparaison ECAM5 vs modèle."""

from __future__ import annotations

from pathlib import Path

from src.reports.ecam5_dashboard import build_ecam5_model_comparison

ROOT = Path(__file__).resolve().parents[1]


def test_build_ecam5_comparison():
    table = build_ecam5_model_comparison(ROOT)
    assert not table.empty
    assert "region" in table.columns
    assert "poverty_rate_pct" in table.columns
    assert "mean_predicted_wealth" in table.columns
    assert "rank_gap" in table.columns
    assert len(table) >= 5