
"""
Fonctions pour classer les zones selon l'indice de priorisation.
"""

import pandas as pd
import geopandas as gpd


def get_top_priority_zones(gdf, priority_col="priority_index", top_n=50):
    """Retourne les zones les plus prioritaires."""
    return gdf.nlargest(top_n, priority_col)