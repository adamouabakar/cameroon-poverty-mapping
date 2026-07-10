"""
Module de priorisation spatiale (Phase 2).
Combine pauvreté estimée + critères d'accessibilité.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import yaml


def load_prioritization_config(path: str | Path) -> dict:
    """Charge les critères de priorisation depuis YAML."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration priorisation introuvable : {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _valid_mask(*arrays: np.ndarray, nodata: float | None = -9999.0) -> np.ndarray:
    mask = np.ones(arrays[0].shape, dtype=bool)
    for arr in arrays:
        mask &= np.isfinite(arr)
        if nodata is not None:
            mask &= arr != nodata
    return mask


def normalize_component(
    values: np.ndarray,
    vmin: float,
    vmax: float,
    *,
    invert: bool = False,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Normalise un composant sur [0, 1] ; valeurs invalides → nodata."""
    out = np.full(values.shape, nodata, dtype=np.float32)
    mask = _valid_mask(values, nodata=nodata)
    if not mask.any():
        return out

    span = vmax - vmin
    if span <= 0:
        normed = np.zeros(values.shape, dtype=np.float32)
    else:
        normed = np.clip((values - vmin) / span, 0.0, 1.0).astype(np.float32)

    if invert:
        normed = (1.0 - normed).astype(np.float32)

    out[mask] = normed[mask]
    return out


def compute_priority_index(
    gdf: gpd.GeoDataFrame,
    wealth_column: str = "predicted_wealth",
    weights: dict | None = None,
    *,
    dist_school_col: str = "dist_school_km",
    dist_health_col: str = "dist_health_km",
    dist_road_col: str = "dist_road_km",
) -> gpd.GeoDataFrame:
    """
    Calcule un indice de priorisation composite sur des entités vectorielles.
    """
    if weights is None:
        weights = {
            "poverty": 0.5,
            "dist_school": 0.2,
            "dist_health": 0.2,
            "dist_road": 0.1,
        }

    cols = {
        "poverty": wealth_column,
        "dist_school": dist_school_col,
        "dist_health": dist_health_col,
        "dist_road": dist_road_col,
    }

    normed = {}
    for key, col in cols.items():
        if col not in gdf.columns:
            raise KeyError(f"Colonne manquante pour {key}: {col}")
        vals = gdf[col].to_numpy(dtype=float)
        vmin, vmax = np.nanpercentile(vals, [5, 95])
        invert = key == "poverty"
        normed[key] = normalize_component(vals, vmin, vmax, invert=invert)

    priority = np.zeros(len(gdf), dtype=np.float32)
    for key, w in weights.items():
        arr = normed[key]
        valid = arr != -9999.0
        priority[valid] += w * arr[valid]

    out = gdf.copy()
    out["priority_index"] = priority
    return out


def combine_normalized_components(
    components: dict[str, np.ndarray],
    weights: dict[str, float],
    *,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Agrège des composants déjà normalisés [0, 1] en indice de priorité."""
    shape = next(iter(components.values())).shape
    priority = np.zeros(shape, dtype=np.float32)
    coverage = np.zeros(shape, dtype=np.float32)

    for key, w in weights.items():
        arr = components[key]
        valid = _valid_mask(arr, nodata=nodata)
        priority[valid] += w * arr[valid]
        coverage[valid] += w

    out = np.full(shape, nodata, dtype=np.float32)
    has_data = coverage > 0
    out[has_data] = priority[has_data] / coverage[has_data]
    return out