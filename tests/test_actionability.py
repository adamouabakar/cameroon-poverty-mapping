"""Tests actionability index."""

from __future__ import annotations

import pandas as pd

from src.simulation.actionability import compute_actionability_index


def test_compute_actionability_index():
    df = pd.DataFrame(
        {
            "predicted_wealth": [-100.0, 50.0, 200.0],
            "dist_road_km": [10.0, 5.0, 1.0],
            "dist_school_km": [8.0, 4.0, 2.0],
            "dist_health_km": [12.0, 6.0, 3.0],
            "accessibility_inverse": [0.05, 0.1, 0.5],
            "uncertainty_width": [5000.0, 3000.0, 1000.0],
        }
    )
    out = compute_actionability_index(df)
    assert "actionability_index" in out.columns
    assert out["actionability_index"].max() >= out["actionability_index"].min()