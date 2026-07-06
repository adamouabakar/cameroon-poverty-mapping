"""Contrôles qualité sur les features extraites."""

from __future__ import annotations

import pandas as pd

FEATURE_RANGES = {
    "ndvi_mean": (-0.2, 1.0),
    "ndbi_mean": (-1.0, 1.0),
    "night_lights_mean": (0.0, 200.0),
    "dist_road_km": (0.0, 100.0),
    "dist_school_km": (0.0, 100.0),
    "dist_health_km": (0.0, 100.0),
    "pop_density": (0.0, 1e6),
    "elevation_m": (-100.0, 5000.0),
    "slope_deg": (0.0, 90.0),
    "built_density": (0.0, 1.0),
    "ghsl_built_fraction": (0.0, 1.0),
    "precip_annual_mm": (0.0, 5000.0),
    "precip_wet_season_mm": (0.0, 5000.0),
    "precip_cv": (0.0, 5.0),
}


def validate_features(df: pd.DataFrame, feature_cols: list[str]) -> dict:
    """Retourne un rapport QA ; lève si valeurs manquantes."""
    report = {"n_rows": len(df), "checks": [], "passed": True}

    if df[feature_cols].isna().any().any():
        report["passed"] = False
        report["checks"].append({"check": "missing_values", "status": "fail"})
        raise ValueError("Valeurs manquantes détectées dans les features GEE.")

    report["checks"].append({"check": "missing_values", "status": "pass"})

    for col in feature_cols:
        if col not in FEATURE_RANGES:
            continue
        low, high = FEATURE_RANGES[col]
        col_min = float(df[col].min())
        col_max = float(df[col].max())
        in_range = (col_min >= low) and (col_max <= high)
        status = "pass" if in_range else "warn"
        if not in_range:
            report["passed"] = False
        report["checks"].append(
            {
                "check": f"range_{col}",
                "status": status,
                "min": col_min,
                "max": col_max,
                "expected": [low, high],
            }
        )

    return report