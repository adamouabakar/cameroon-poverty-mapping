"""
Chargement des données préparées et construction de la matrice d'entraînement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import geopandas as gpd
import pandas as pd

DEFAULT_EXCLUDE_COLS = [
    "geometry",
    "buffer_km",
    "wealth_index",
    "latitude",
    "longitude",
]


def load_prepared_clusters(path: str | Path) -> gpd.GeoDataFrame:
    """Charge le parquet produit par le Notebook 01."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    return gpd.read_parquet(path)


def build_training_matrix(
    df: pd.DataFrame,
    feature_cols: list[str],
    target: str = "wealth_index",
    exclude_cols: list[str] | None = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """
    Retourne X, y et meta (identifiants + stratification).
    """
    exclude_cols = exclude_cols or DEFAULT_EXCLUDE_COLS
    missing_features = [c for c in feature_cols if c not in df.columns]
    if missing_features:
        raise ValueError(f"Features manquantes : {missing_features}")
    if target not in df.columns:
        raise ValueError(f"Colonne cible introuvable : {target}")

    meta_cols = [
        c for c in ["cluster_id", "region", "urban_rural", "fold_id"] if c in df.columns
    ]
    meta = df[meta_cols].copy()

    X = df[feature_cols].copy()
    y = df[target].copy()

    if X.isna().any().any():
        raise ValueError("La matrice X contient des valeurs manquantes.")
    if y.isna().any():
        raise ValueError("La cible contient des valeurs manquantes.")

    return X, y, meta