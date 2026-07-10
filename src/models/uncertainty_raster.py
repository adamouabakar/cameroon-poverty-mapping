"""
Carte d'incertitude alignée sur la grille raster wealth (inférence GEE directe).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.interpolate import Rbf

from src.visualization.export_geotiff import array_to_geotiff
from src.visualization.static_maps import merge_oof_with_clusters


def _cluster_uncertainty_half_width(oof: pd.DataFrame) -> pd.Series:
    if "uncertainty_half_width" in oof.columns:
        return oof["uncertainty_half_width"]
    return (oof["upper_90"] - oof["lower_90"]) / 2.0


def export_uncertainty_on_wealth_grid(
    wealth_raster_path: str | Path,
    clusters_gdf: gpd.GeoDataFrame,
    oof_df: pd.DataFrame,
    output_path: str | Path,
    *,
    nodata: float = -9999.0,
    smooth: float = 0.1,
) -> Path:
    """
    Interpole la demi-largeur d'incertitude OOF (430 grappes) sur la grille
    du raster wealth modèle (même extent / résolution).
    """
    wealth_raster_path = Path(wealth_raster_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = merge_oof_with_clusters(clusters_gdf, oof_df)
    gdf["uncertainty_half_width"] = _cluster_uncertainty_half_width(gdf)

    with rasterio.open(wealth_raster_path) as src:
        transform = src.transform
        height, width = src.height, src.width
        crs = src.crs
        wealth_nodata = src.nodata if src.nodata is not None else nodata
        wealth_mask = src.read(1) == wealth_nodata if wealth_nodata is not None else None

    pts = gdf.to_crs(crs)
    cx = pts.geometry.centroid.x.to_numpy()
    cy = pts.geometry.centroid.y.to_numpy()
    values = pts["uncertainty_half_width"].to_numpy(dtype=float)

    col_idx = np.arange(width)
    row_idx = np.arange(height)
    xx, yy = np.meshgrid(col_idx, row_idx)
    xs, ys = rasterio.transform.xy(transform, yy.ravel(), xx.ravel(), offset="center")
    gx = np.array(xs, dtype=float).reshape(height, width)
    gy = np.array(ys, dtype=float).reshape(height, width)

    rbf = Rbf(cx, cy, values, function="multiquadric", smooth=smooth)
    grid_z = rbf(gx, gy).astype(np.float32)

    if wealth_mask is not None:
        grid_z = np.where(wealth_mask, nodata, grid_z)
    grid_z[~np.isfinite(grid_z)] = nodata

    array_to_geotiff(grid_z, str(output_path), transform, crs=str(crs), nodata=nodata)
    return output_path