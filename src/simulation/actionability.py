"""Indice d'actionnabilité — priorité × accessibilité × confiance modèle."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.simulation.prioritization import compute_priority_index, normalize_component


def compute_actionability_index(
    df: pd.DataFrame,
    *,
    wealth_col: str = "predicted_wealth",
    accessibility_col: str = "accessibility_inverse",
    uncertainty_width_col: str = "uncertainty_width",
    priority_weights: dict | None = None,
) -> pd.DataFrame:
    """
    Combine priorité composite, potentiel accessibilité (v5_post) et confiance OOF.

    actionability = priority × (0.6 + 0.4 × accessibility_norm) × confidence
    confidence = 1 - uncertainty_norm (incertitude faible → plus actionnable)
    """
    if priority_weights is None:
        priority_weights = {
            "poverty": 0.45,
            "dist_school": 0.2,
            "dist_health": 0.2,
            "dist_road": 0.15,
        }

    out = compute_priority_index(df, wealth_column=wealth_col, weights=priority_weights)

    acc = out[accessibility_col].to_numpy(dtype=float)
    acc_norm = normalize_component(acc, *np.nanpercentile(acc, [5, 95]))

    if uncertainty_width_col in out.columns:
        unc = out[uncertainty_width_col].to_numpy(dtype=float)
        unc_norm = normalize_component(unc, *np.nanpercentile(unc, [5, 95]))
        confidence = np.clip(1.0 - unc_norm, 0.0, 1.0)
    else:
        confidence = np.ones(len(out), dtype=np.float32)

    priority = out["priority_index"].to_numpy(dtype=float)
    actionability = priority * (0.6 + 0.4 * acc_norm) * confidence
    actionability[acc_norm == -9999.0] = -9999.0

    out["actionability_index"] = actionability.astype(np.float32)
    out["confidence_factor"] = confidence.astype(np.float32)
    return out


def top_actionable_zones(df: pd.DataFrame, *, top_n: int = 30) -> pd.DataFrame:
    """Retourne les zones les plus actionnables (indice décroissant)."""
    valid = df[df["actionability_index"] > -9999.0].copy()
    return valid.sort_values("actionability_index", ascending=False).head(top_n)