"""
Fonctions pour sauvegarder et charger des modèles.
"""

import joblib
from pathlib import Path


def save_model(model, filepath: str | Path):
    """Sauvegarde un modèle avec joblib."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, filepath)


def load_model(filepath: str | Path):
    """Charge un modèle sauvegardé."""
    return joblib.load(filepath)