"""
Module pour l'extraction de features à partir d'images satellitaires
(Sentinel-2, Landsat, etc.).
"""

import pandas as pd
import geopandas as gpd


def extract_imagery_features(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Extrait des features à partir d'images satellitaires.
    TODO: Implémenter l'extraction (moyenne, variance, indices spectraux, etc.).
    """
    features = pd.DataFrame(index=gdf.index)
    return features