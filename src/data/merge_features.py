"""
Module pour fusionner les features extraites avec les labels DHS.
"""

import pandas as pd
import geopandas as gpd


def merge_dhs_with_features(
    dhs_gdf: gpd.GeoDataFrame,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """Joint les grappes DHS avec les features tabulaires sur cluster_id."""
    dhs_df = dhs_gdf.drop(columns=["geometry"], errors="ignore").copy()

    if "cluster_id" not in features_df.columns:
        features_df = features_df.copy()
        features_df["cluster_id"] = dhs_df["cluster_id"].values

    merged = pd.merge(dhs_df, features_df, on="cluster_id", how="left", validate="one_to_one")
    if merged[features_df.columns.drop("cluster_id", errors="ignore")].isna().any().any():
        raise ValueError("Jointure incomplète entre DHS et features.")
    return merged