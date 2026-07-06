"""
Module d'extraction des features tabulaires 
(night lights, distances OSM, WorldPop, topographie...).
"""

import pandas as pd
import geopandas as gpd


def extract_tabular_features(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Extrait les features tabulaires à partir d'un GeoDataFrame.
    
    TODO: Implémenter l'extraction réelle des features 
    (night lights, distances OSM, WorldPop, etc.).
    """
    features = pd.DataFrame(index=gdf.index)
    
    # Placeholder - à compléter plus tard
    # Exemples de features à ajouter :
    # - night_lights_mean
    # - distance_to_road
    # - population_density
    # - elevation_mean
    
    return features