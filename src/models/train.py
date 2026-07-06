"""
Fonctions d'entraînement du modèle de richesse.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.models.hybrid_model import HybridWealthModel
from src.utils.config import load_config


def create_model(config: dict | None = None) -> HybridWealthModel:
    """Instancie un modèle LightGBM à partir de la configuration."""
    if config is None:
        config = load_config()

    params = config["model"].get("params", {}).copy()
    params["random_state"] = config["model"].get("random_state", 42)
    return HybridWealthModel(params=params)


def train_final_model(
    X: pd.DataFrame,
    y: pd.Series,
    config: dict,
    median_best_iteration: int,
    strata: pd.Series | None = None,
) -> HybridWealthModel:
    """
    Entraîne le modèle final sur toutes les grappes.
    Destiné à l'inférence — les métriques de référence restent celles de la CV OOF.
    """
    model_cfg = config["model"]
    params = model_cfg.get("params", {}).copy()
    params["random_state"] = model_cfg.get("random_state", 42)
    params["n_estimators"] = int(median_best_iteration)

    val_fraction = float(model_cfg.get("internal_val_fraction", 0.15))
    random_state = int(model_cfg.get("random_state", 42))
    early_stopping_rounds = int(model_cfg.get("early_stopping_rounds", 30))

    if strata is not None and strata.nunique() > 1:
        try:
            X_train, X_val, y_train, y_val = train_test_split(
                X,
                y,
                test_size=val_fraction,
                random_state=random_state,
                stratify=strata,
            )
        except ValueError:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=val_fraction, random_state=random_state
            )
    else:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=val_fraction, random_state=random_state
        )

    model = HybridWealthModel(params=params)
    model.fit(
        X_train,
        y_train,
        X_val=X_val,
        y_val=y_val,
        early_stopping_rounds=early_stopping_rounds,
    )
    return model


def train_model(X_train: pd.DataFrame, y_train: pd.Series, config: dict | None = None):
    """Entraîne un modèle sans validation interne (compatibilité legacy)."""
    if config is None:
        config = load_config()
    model = create_model(config)
    model.fit(X_train, y_train, early_stopping_rounds=None)
    return model


def extract_median_best_iteration(cv_results) -> int:
    """Retourne la médiane des meilleures itérations issues de la CV."""
    if not cv_results.best_iterations:
        return 100
    return int(np.median(cv_results.best_iterations))