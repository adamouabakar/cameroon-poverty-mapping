"""
Fonctions pour faire des prédictions avec un modèle entraîné.
"""

import pandas as pd
import joblib
from pathlib import Path


def load_model(model_path: str | Path):
    """Charge un modèle sauvegardé."""
    return joblib.load(model_path)


def predict_wealth(model, X: pd.DataFrame) -> pd.Series:
    """Effectue des prédictions d'indice de richesse."""
    predictions = model.predict(X)
    return pd.Series(predictions, index=X.index, name="predicted_wealth")