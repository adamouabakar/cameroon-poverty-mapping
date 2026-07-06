"""Post-traitement des extractions GEE vers le schéma Notebook 02."""

from __future__ import annotations

import pandas as pd


def features_to_model_schema(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Renomme les bandes GEE vers les 10 colonnes attendues par le modèle.
    Convertit les distances m → km.
    """
    band_map = config["band_names"]
    feature_cols = config["feature_columns"]

    rename_map = {band_map[col]: col for col in feature_cols if band_map[col] in df.columns}
    out = df.rename(columns=rename_map)

    for dist_col in ["dist_road_km", "dist_school_km", "dist_health_km"]:
        if dist_col in out.columns:
            out[dist_col] = out[dist_col] / 1000.0

    missing = [c for c in feature_cols if c not in out.columns]
    if missing:
        raise ValueError(f"Colonnes features manquantes après postprocess : {missing}")

    if "cluster_id" not in out.columns:
        raise ValueError("cluster_id manquant dans l'extraction GEE.")

    return out[["cluster_id"] + feature_cols]