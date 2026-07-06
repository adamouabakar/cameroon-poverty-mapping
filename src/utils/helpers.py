"""
Fonctions utilitaires diverses.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


def get_project_root() -> Path:
    """Retourne la racine du projet (dossier contenant configs/)."""
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        if (parent / "configs" / "default.yaml").exists():
            return parent
    raise FileNotFoundError("Racine du projet introuvable (configs/default.yaml).")


def hash_config_file(config_path: str | Path) -> str:
    """Calcule un hash MD5 du fichier de configuration."""
    config_path = Path(config_path)
    content = config_path.read_bytes()
    return hashlib.md5(content).hexdigest()


def normalize_column(series: pd.Series, method: str = "minmax"):
    """Normalise une colonne (min-max ou z-score)."""
    if method == "minmax":
        return (series - series.min()) / (series.max() - series.min())
    elif method == "zscore":
        return (series - series.mean()) / series.std()
    else:
        raise ValueError("Méthode de normalisation non supportée.")


def safe_divide(a, b):
    """Division sécurisée (évite la division par zéro)."""
    return np.divide(a, b, out=np.zeros_like(a, dtype=float), where=b != 0)