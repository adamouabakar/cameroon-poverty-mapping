"""
Chargement des features par grappe — fictives ou GEE selon la configuration.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.features.generate_fake_features import generate_fake_geospatial_features
from src.utils.helpers import get_project_root


def resolve_feature_source(config: dict) -> str:
    """
    Retourne 'fake' ou 'gee'.

    Priorité :
    - `features.source == 'gee'` → GEE
    - `features.fake == False` → GEE
    - sinon → fake
    """
    features_cfg = config.get("features", {})
    source = str(features_cfg.get("source", "fake")).lower()

    if source == "gee" or not features_cfg.get("fake", True):
        return "gee"
    return "fake"


def load_cluster_features(
    gdf: gpd.GeoDataFrame,
    config: dict,
    project_root: Path | None = None,
) -> tuple[pd.DataFrame, str]:
    """
    Charge les features alignées sur les grappes du GeoDataFrame.

    Returns
    -------
    features_df : DataFrame avec cluster_id + colonnes features
    source : 'fake' | 'gee'
    """
    root = project_root or get_project_root()
    features_cfg = config["features"]
    feature_cols = features_cfg["columns"]
    source = resolve_feature_source(config)

    if source == "fake":
        features_df = generate_fake_geospatial_features(
            gdf,
            random_state=config["model"]["random_state"],
        )
        return features_df, "fake"

    gee_path = root / features_cfg.get(
        "gee_parquet", "data/processed/features/cluster_features_gee.parquet"
    )
    if not gee_path.exists():
        raise FileNotFoundError(
            f"Features GEE introuvables : {gee_path}. "
            "Exécutez d'abord scripts/extract_gee_features.py ou le Notebook 03."
        )

    features_df = pd.read_parquet(gee_path)
    missing = [c for c in ["cluster_id", *feature_cols] if c not in features_df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans {gee_path} : {missing}")

    cluster_ids = set(gdf["cluster_id"].tolist())
    available = set(features_df["cluster_id"].tolist())
    if not cluster_ids.issubset(available):
        missing_ids = sorted(cluster_ids - available)
        raise ValueError(
            f"Features GEE incomplètes pour {len(missing_ids)} grappes. "
            f"Exemples manquants : {missing_ids[:5]}"
        )

    features_df = features_df.loc[
        features_df["cluster_id"].isin(cluster_ids), ["cluster_id", *feature_cols]
    ].copy()

    if features_df[feature_cols].isna().any().any():
        raise ValueError("Les features GEE contiennent des valeurs manquantes.")

    return features_df, "gee"