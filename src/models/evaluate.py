"""
Fonctions d'évaluation des modèles.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def compute_metrics(y_true, y_pred) -> dict:
    """Calcule R², RMSE et MAE."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
    }


def compute_spearman(y_true, y_pred) -> float:
    """Corrélation de Spearman entre observations et prédictions."""
    rho, _ = spearmanr(y_true, y_pred)
    return float(rho)


def evaluate_by_strata(
    y_true: pd.Series,
    y_pred: pd.Series,
    strata: pd.Series,
) -> pd.DataFrame:
    """Métriques de régression par strate (urbain/rural, région, etc.)."""
    rows = []
    aligned = pd.DataFrame({"y_true": y_true, "y_pred": y_pred, "strata": strata})

    for stratum, group in aligned.groupby("strata"):
        metrics = compute_metrics(group["y_true"], group["y_pred"])
        metrics["spearman"] = compute_spearman(group["y_true"], group["y_pred"])
        metrics["stratum"] = stratum
        metrics["n"] = len(group)
        rows.append(metrics)

    return pd.DataFrame(rows)[["stratum", "n", "r2", "rmse", "mae", "spearman"]]


def build_cv_report(
    fold_metrics: list[dict],
    global_metrics: dict,
    config_hash: str,
    cv_strategy: str,
    fake_data: bool = True,
) -> dict:
    """Structure JSON sérialisable pour outputs/reports/cv_metrics.json."""
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_hash": config_hash,
        "cv_strategy": cv_strategy,
        "fake_data": fake_data,
        "global_oof_metrics": global_metrics,
        "fold_metrics": fold_metrics,
    }