"""
Module de priorisation spatiale (Phase 2).
Combine pauvreté estimée + critères d'accessibilité.
"""

import pandas as pd
import geopandas as gpd
import numpy as np


def compute_priority_index(
    gdf: gpd.GeoDataFrame,
    wealth_column: str = "predicted_wealth",
    weights: dict = None
) -> gpd.GeoDataFrame:
    """
    Calcule un indice de priorisation composite.
    
    TODO: Implémenter la normalisation et l'agrégation des critères.
    """
    if weights is None:
        weights = {
            "poverty": 0.5,
            "distance_to_school": 0.2,
            "distance_to_health": 0.2,
            "distance_to_road": 0.1
        }

    # Placeholder
    gdf["priority_index"] = 0.0
    return gdf