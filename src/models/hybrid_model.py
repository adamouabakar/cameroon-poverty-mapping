"""
Modèle hybride tabulaire basé sur LightGBM.
"""

from __future__ import annotations

from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin


class HybridWealthModel(BaseEstimator, RegressorMixin):
    """Wrapper LightGBM avec early stopping optionnel."""

    def __init__(self, params: dict | None = None):
        self.params = params or {
            "objective": "regression",
            "metric": "rmse",
            "verbosity": -1,
            "random_state": 42,
        }
        self.model: lgb.Booster | None = None
        self.best_iteration_: int | None = None
        self.feature_names_: list[str] | None = None

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        early_stopping_rounds: int | None = 30,
    ) -> "HybridWealthModel":
        train_params = self.params.copy()
        num_boost_round = int(train_params.pop("n_estimators", 1000))

        self.feature_names_ = list(X.columns)
        y_array = pd.Series(y).to_numpy()
        train_data = lgb.Dataset(X, label=y_array, feature_name=self.feature_names_)

        valid_sets = [train_data]
        valid_names = ["train"]
        callbacks: list[Any] = []

        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(
                X_val,
                label=pd.Series(y_val).to_numpy(),
                reference=train_data,
                feature_name=self.feature_names_,
            )
            valid_sets.append(val_data)
            valid_names.append("valid")
            if early_stopping_rounds:
                callbacks.append(
                    lgb.early_stopping(
                        stopping_rounds=early_stopping_rounds, verbose=False
                    )
                )

        self.model = lgb.train(
            train_params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks,
        )

        if X_val is not None and hasattr(self.model, "best_iteration"):
            self.best_iteration_ = self.model.best_iteration
        else:
            self.best_iteration_ = self.model.current_iteration()

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Le modèle n'est pas entraîné.")
        num_iteration = self.best_iteration_ or self.model.current_iteration()
        return self.model.predict(X, num_iteration=num_iteration)

    def feature_importance(self, importance_type: str = "gain") -> pd.DataFrame:
        if self.model is None or self.feature_names_ is None:
            raise RuntimeError("Le modèle n'est pas entraîné.")
        values = self.model.feature_importance(importance_type=importance_type)
        return (
            pd.DataFrame({"feature": self.feature_names_, "gain": values})
            .sort_values("gain", ascending=False)
            .reset_index(drop=True)
        )