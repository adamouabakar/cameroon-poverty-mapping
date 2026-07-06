"""
Génération de features géospatiales fictives pour le pipeline structurel.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

FAKE_FEATURE_COLUMNS = [
    "night_lights_mean",
    "ndvi_mean",
    "ndbi_mean",
    "dist_road_km",
    "dist_school_km",
    "dist_health_km",
    "pop_density",
    "elevation_m",
    "slope_deg",
    "built_density",
]

MAX_TARGET_CORRELATION = 0.3


def generate_fake_geospatial_features(
    gdf: gpd.GeoDataFrame,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Génère exactement 10 features plausibles, décorrélées de wealth_index.
    Une corrélation modérée avec urban_rural est autorisée (réalisme documenté).
    """
    if "cluster_id" not in gdf.columns:
        raise ValueError("Le GeoDataFrame doit contenir la colonne cluster_id.")

    rng = np.random.default_rng(random_state)
    n = len(gdf)
    is_urban = (gdf["urban_rural"] == "urban").to_numpy()

    features = pd.DataFrame(
        {
            "cluster_id": gdf["cluster_id"].to_numpy(),
            "night_lights_mean": rng.uniform(0, 20, n) + is_urban * rng.uniform(10, 40, n),
            "ndvi_mean": rng.normal(0.45, 0.12, n),
            "ndbi_mean": rng.normal(0.05, 0.08, n) + is_urban * 0.12,
            "dist_road_km": rng.exponential(3.0, n),
            "dist_school_km": rng.exponential(2.5, n),
            "dist_health_km": rng.exponential(4.0, n),
            "pop_density": rng.lognormal(mean=4.0, sigma=0.8, size=n) * (1 + is_urban * 4),
            "elevation_m": rng.uniform(0, 2800, n),
            "slope_deg": rng.gamma(shape=2.0, scale=3.0, size=n),
            "built_density": rng.beta(1.5, 5.0, n) + is_urban * rng.beta(4.0, 2.0, n) * 0.5,
        }
    )

    assert list(features.columns[1:]) == FAKE_FEATURE_COLUMNS
    assert features.shape[1] == 11  # cluster_id + 10 features
    assert features.isna().sum().sum() == 0

    if "wealth_index" in gdf.columns:
        _validate_low_target_correlation(features, gdf["wealth_index"])

    return features


def _validate_low_target_correlation(
    features: pd.DataFrame,
    wealth_index: pd.Series,
    max_corr: float = MAX_TARGET_CORRELATION,
) -> None:
    for col in FAKE_FEATURE_COLUMNS:
        corr = np.corrcoef(features[col], wealth_index)[0, 1]
        if abs(corr) >= max_corr:
            raise ValueError(
                f"Corrélation trop élevée entre {col} et wealth_index ({corr:.3f}). "
                f"Seuil : {max_corr}."
            )