"""
Estimation conservative de l'incertitude à partir des résidus OOF.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_residual_uncertainty(
    oof_residuals: pd.Series,
    confidence: float = 0.90,
) -> dict:
    """
    Calcule une incertitude globale à partir de la distribution des résidus OOF.
    Approximation conservative — pas un intervalle de confiance sur la vérité terrain.
    """
    abs_residuals = oof_residuals.abs()
    alpha = confidence
    q = float(np.quantile(abs_residuals, alpha))

    return {
        "confidence_level": confidence,
        "residual_std": float(oof_residuals.std(ddof=1)),
        "residual_q90": q,
        "interval_half_width": q,
        "method": "global_residual_quantile_oof",
        "note": (
            "Approximation conservative basée sur les résidus OOF globaux. "
            "Ne pas utiliser pour décisions opérationnelles."
        ),
    }


def attach_prediction_intervals(
    oof_predictions: pd.Series,
    y_true: pd.Series,
    uncertainty: dict,
    meta: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attache des bandes ±q90 autour des prédictions OOF."""
    half_width = uncertainty["interval_half_width"]
    residuals = y_true - oof_predictions

    result = pd.DataFrame(
        {
            "y_true": y_true.values,
            "y_oof_pred": oof_predictions.values,
            "residual": residuals.values,
            "lower_90": oof_predictions.values - half_width,
            "upper_90": oof_predictions.values + half_width,
        },
        index=oof_predictions.index,
    )

    if meta is not None:
        for col in meta.columns:
            result[col] = meta[col].values

    return result.reset_index(drop=True)