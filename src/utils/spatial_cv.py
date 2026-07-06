"""
Validation croisée spatiale pour grappes DHS.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from sklearn.cluster import KMeans


def _cluster_coordinates(
    gdf: gpd.GeoDataFrame,
    crs_projected: int = 32633,
) -> tuple[np.ndarray, np.ndarray]:
    """Retourne les coordonnées de centroïde des grappes (points ou buffers)."""
    if "latitude" in gdf.columns and "longitude" in gdf.columns:
        points = gpd.GeoSeries(
            [
                Point(lon, lat)
                for lon, lat in zip(gdf["longitude"], gdf["latitude"])
            ],
            crs="EPSG:4326",
        )
        projected = points.to_crs(epsg=crs_projected)
        return projected.x.to_numpy(), projected.y.to_numpy()

    gdf_proj = gdf.to_crs(epsg=crs_projected)
    centroids = gdf_proj.geometry.centroid
    return centroids.x.to_numpy(), centroids.y.to_numpy()


def assign_spatial_blocks(
    gdf: gpd.GeoDataFrame,
    n_folds: int = 5,
    crs_projected: int = 32633,
    method: str = "grid",
    random_state: int = 42,
) -> pd.Series:
    """Assigne chaque grappe à un bloc spatial (fold_id de 0 à n_folds-1)."""
    if len(gdf) < n_folds:
        raise ValueError(
            f"Nombre de grappes ({len(gdf)}) insuffisant pour {n_folds} plis."
        )

    xs, ys = _cluster_coordinates(gdf, crs_projected=crs_projected)

    if method == "kmeans":
        coords = np.column_stack([xs, ys])
        km = KMeans(n_clusters=n_folds, random_state=random_state, n_init=10)
        fold_ids = km.fit_predict(coords)
        return pd.Series(fold_ids, index=gdf.index, name="fold_id")

    n_cols = 3 if n_folds >= 5 else n_folds
    n_rows = int(np.ceil(n_folds / n_cols))

    x_edges = np.linspace(xs.min(), xs.max(), n_cols + 1)
    y_edges = np.linspace(ys.min(), ys.max(), n_rows + 1)

    x_bin = np.clip(np.digitize(xs, x_edges[1:-1]), 0, n_cols - 1)
    y_bin = np.clip(np.digitize(ys, y_edges[1:-1]), 0, n_rows - 1)
    cell_id = y_bin * n_cols + x_bin

    unique_cells = sorted(np.unique(cell_id))
    cell_to_fold = {cell: i % n_folds for i, cell in enumerate(unique_cells)}
    fold_values = np.array([cell_to_fold[c] for c in cell_id])

    return pd.Series(fold_values, index=gdf.index, name="fold_id")


def block_based_cv(
    gdf: gpd.GeoDataFrame,
    n_folds: int = 5,
    method: str = "grid",
    random_state: int = 42,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Yield (train_idx, val_idx) avec séparation par blocs spatiaux."""
    fold_ids = assign_spatial_blocks(
        gdf, n_folds=n_folds, method=method, random_state=random_state
    )

    for fold in range(n_folds):
        val_mask = fold_ids == fold
        val_idx = np.where(val_mask.to_numpy())[0]
        train_idx = np.where((~val_mask).to_numpy())[0]
        if len(val_idx) == 0 or len(train_idx) == 0:
            continue
        yield train_idx, val_idx


def region_based_cv(
    gdf: gpd.GeoDataFrame,
    region_col: str = "region",
    n_folds: int = 5,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Repli : regroupe les régions administratives en n_folds."""
    regions = sorted(gdf[region_col].unique())
    if len(regions) < n_folds:
        raise ValueError(
            f"Nombre de régions ({len(regions)}) insuffisant pour {n_folds} plis."
        )

    region_to_fold = {
        region: i % n_folds for i, region in enumerate(regions)
    }
    fold_ids = gdf[region_col].map(region_to_fold)

    for fold in range(n_folds):
        val_mask = fold_ids == fold
        val_idx = np.where(val_mask.to_numpy())[0]
        train_idx = np.where((~val_mask).to_numpy())[0]
        if len(val_idx) == 0 or len(train_idx) == 0:
            continue
        yield train_idx, val_idx


def validate_fold_balance(
    gdf: gpd.GeoDataFrame,
    fold_ids: pd.Series,
    min_val_size: int = 5,
    require_urban_rural: bool = True,
    urban_rural_col: str = "urban_rural",
) -> dict:
    """Vérifie l'équilibre des plis ; retourne un rapport et un booléen is_balanced."""
    fold_reports = []
    is_balanced = True

    for fold in sorted(fold_ids.unique()):
        val_mask = fold_ids == fold
        val_gdf = gdf.loc[val_mask]
        n_val = len(val_gdf)

        report = {
            "fold": int(fold),
            "n_val": n_val,
            "n_train": int((~val_mask).sum()),
        }

        if n_val < min_val_size:
            is_balanced = False
            report["warning"] = f"n_val < {min_val_size}"

        if require_urban_rural and n_val > 0:
            strata = val_gdf[urban_rural_col].value_counts().to_dict()
            report["urban_rural_counts"] = strata
            if len(strata) < 2:
                is_balanced = False
                report["warning"] = "validation fold missing urban or rural"

        fold_reports.append(report)

    return {"is_balanced": is_balanced, "folds": fold_reports}


def get_fold_assignments(
    gdf: gpd.GeoDataFrame,
    strategy: str = "block",
    n_folds: int = 5,
    random_state: int = 42,
) -> Tuple[str, pd.Series]:
    """Retourne la stratégie retenue et les fold_id par grappe."""
    if strategy == "region":
        fold_ids = _region_fold_series(gdf, n_folds=n_folds)
        return "region", fold_ids

    fold_ids = assign_spatial_blocks(
        gdf, n_folds=n_folds, method="grid", random_state=random_state
    )
    return "block", fold_ids


def select_cv_strategy(
    gdf: gpd.GeoDataFrame,
    preferred: str = "block",
    n_folds: int = 5,
    min_val_size: int = 5,
    random_state: int = 42,
) -> Tuple[str, pd.Series, dict]:
    """
    Tente block_based_cv ; bascule sur region si les plis sont déséquilibrés.
    Retourne (strategy, fold_ids, balance_report).
    """
    if preferred == "region":
        fold_ids = _region_fold_series(gdf, n_folds=n_folds)
        report = validate_fold_balance(gdf, fold_ids, min_val_size=min_val_size)
        return "region", fold_ids, report

    if preferred == "auto" or preferred == "block":
        _, fold_ids = get_fold_assignments(
            gdf, strategy="block", n_folds=n_folds, random_state=random_state
        )
        report = validate_fold_balance(gdf, fold_ids, min_val_size=min_val_size)
        if report["is_balanced"]:
            return "block", fold_ids, report

        fold_ids = _region_fold_series(gdf, n_folds=n_folds)
        report = validate_fold_balance(gdf, fold_ids, min_val_size=min_val_size)
        return "region", fold_ids, report

    raise ValueError(f"Stratégie CV inconnue : {preferred}")


def iter_cv_splits(
    fold_ids: pd.Series,
    n_folds: int,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Génère les splits train/val à partir de fold_ids assignés."""
    for fold in range(n_folds):
        val_mask = fold_ids == fold
        if not val_mask.any():
            continue
        val_idx = np.where(val_mask.to_numpy())[0]
        train_idx = np.where((~val_mask).to_numpy())[0]
        yield train_idx, val_idx


def _region_fold_series(gdf: gpd.GeoDataFrame, n_folds: int) -> pd.Series:
    regions = sorted(gdf["region"].unique())
    region_to_fold = {region: i % n_folds for i, region in enumerate(regions)}
    return gdf["region"].map(region_to_fold).rename("fold_id")