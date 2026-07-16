"""Tests alertes régionales watchlist."""

from __future__ import annotations

import pandas as pd

from src.reports.watchlist import evaluate_watchlist, format_alerts_text


def _sample_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"region": "Tout le Cameroun", "uncertainty_mean": 30000, "wealth_mean": -50000},
            {"region": "Extrême-Nord", "uncertainty_mean": 50000, "wealth_mean": -90000},
            {"region": "Centre", "uncertainty_mean": 25000, "wealth_mean": -20000},
        ]
    )


def test_evaluate_watchlist_fires_alerts():
    rules = [
        {"metric": "uncertainty_mean", "threshold": 45000, "direction": "above", "label_fr": "Incertitude"},
        {"metric": "wealth_mean", "threshold": -80000, "direction": "below", "label_fr": "Wealth bas"},
    ]
    alerts = evaluate_watchlist(_sample_summary(), rules, lang="fr")
    assert not alerts.empty
    regions = set(alerts["region"])
    assert "Extrême-Nord" in regions


def test_format_alerts_empty():
    lines = format_alerts_text(pd.DataFrame(), lang="fr")
    assert any("Aucune" in line for line in lines)


def test_format_alerts_with_rows():
    alerts = pd.DataFrame(
        [{"region": "Nord", "metric": "wealth_mean", "value": -90000, "threshold": -80000, "alert_label": "Bas"}]
    )
    lines = format_alerts_text(alerts, lang="fr")
    assert any("Nord" in line for line in lines)