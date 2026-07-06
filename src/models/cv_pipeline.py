"""
Pipeline de validation croisée spatiale avec early stopping LightGBM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.models.evaluate import compute_metrics, compute_spearman
from src.models.hybrid_model import HybridWealthModel
from src.utils.spatial_cv import iter_cv_splits, select_cv_strategy


@dataclass
class CVResults:
    oof_predictions: pd.Series
    oof_residuals: pd.Series
    fold_metrics: list[dict] = field(default_factory=list)
    fold_ids: pd.Series | None = None
    best_iterations: list[int] = field(default_factory=list)
    models: list[HybridWealthModel] = field(default_factory=list)
    cv_strategy: str = "block"


def _internal_split(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    strata: pd.Series | None,
    val_fraction: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    split_kwargs = {
        "test_size": val_fraction,
        "random_state": random_state,
    }
    if strata is not None and strata.nunique() > 1:
        split_kwargs["stratify"] = strata

    try:
        X_inner, X_es, y_inner, y_es = train_test_split(X_train, y_train, **split_kwargs)
    except ValueError:
        split_kwargs.pop("stratify", None)
        X_inner, X_es, y_inner, y_es = train_test_split(X_train, y_train, **split_kwargs)

    return X_inner, y_inner, X_es, y_es


def run_spatial_cv(
    X: pd.DataFrame,
    y: pd.Series,
    gdf: pd.DataFrame,
    config: dict,
    cv_strategy: str | None = None,
    return_models: bool = True,
) -> CVResults:
    """
    Exécute la CV spatiale et retourne les prédictions OOF.
    Les métriques de référence sont uniquement celles des prédictions OOF.
    """
    model_cfg = config["model"]
    n_folds = int(model_cfg["n_folds"])
    random_state = int(model_cfg["random_state"])
    preferred = cv_strategy or model_cfg.get("cv_strategy", "auto")

    strategy, fold_ids, _ = select_cv_strategy(
        gdf,
        preferred=preferred,
        n_folds=n_folds,
        random_state=random_state,
    )

    oof_pred = pd.Series(np.nan, index=X.index, dtype=float)
    fold_metrics: list[dict] = []
    best_iterations: list[int] = []
    models: list[HybridWealthModel] = []

    params = model_cfg.get("params", {}).copy()
    params["random_state"] = random_state
    early_stopping_rounds = int(model_cfg.get("early_stopping_rounds", 30))
    internal_val_fraction = float(model_cfg.get("internal_val_fraction", 0.15))

    for fold_idx, (train_idx, val_idx) in enumerate(
        iter_cv_splits(fold_ids, n_folds=n_folds)
    ):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]

        strata = None
        if "urban_rural" in gdf.columns:
            strata = gdf.iloc[train_idx]["urban_rural"]

        X_inner, y_inner, X_es, y_es = _internal_split(
            X_train,
            y_train,
            strata=strata,
            val_fraction=internal_val_fraction,
            random_state=random_state + fold_idx,
        )

        model = HybridWealthModel(params=params)
        model.fit(
            X_inner,
            y_inner,
            X_val=X_es,
            y_val=y_es,
            early_stopping_rounds=early_stopping_rounds,
        )

        preds = model.predict(X_val)
        oof_pred.iloc[val_idx] = preds

        metrics = compute_metrics(y_val, preds)
        metrics["spearman"] = compute_spearman(y_val, preds)
        metrics["fold"] = fold_idx
        metrics["n_train"] = len(train_idx)
        metrics["n_val"] = len(val_idx)
        metrics["best_iteration"] = int(model.best_iteration_ or 0)
        fold_metrics.append(metrics)

        best_iterations.append(int(model.best_iteration_ or 0))
        if return_models:
            models.append(model)

    oof_residuals = y - oof_pred

    return CVResults(
        oof_predictions=oof_pred,
        oof_residuals=oof_residuals,
        fold_metrics=fold_metrics,
        fold_ids=fold_ids,
        best_iterations=best_iterations,
        models=models,
        cv_strategy=strategy,
    )