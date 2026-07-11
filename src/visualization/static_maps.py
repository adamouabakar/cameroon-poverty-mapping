"""Cartes statiques : grappes, régions, grille interpolée."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib.patches import Patch
from scipy.interpolate import Rbf
from shapely.geometry import box

from src.visualization.export_geotiff import array_to_geotiff

_CAMEROON_CRS = "EPSG:32633"
_WGS84 = "EPSG:4326"

# Villes principales (repères cartographiques)
_MAJOR_CITIES = {
    "Yaoundé": (11.52, 3.87),
    "Douala": (9.70, 4.05),
    "Garoua": (13.40, 9.30),
    "Maroua": (14.32, 10.59),
    "Bafoussam": (10.42, 5.48),
    "Bamenda": (10.16, 5.96),
    "Ngaoundéré": (13.58, 7.32),
}


def merge_oof_with_clusters(
    clusters_gdf: gpd.GeoDataFrame,
    oof_df: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Joint prédictions OOF et intervalles sur les buffers des grappes."""
    oof_cols = [c for c in oof_df.columns if c not in ("region", "urban_rural")]
    merged = clusters_gdf.merge(oof_df[oof_cols], on="cluster_id", how="inner")
    if "wealth_index" in merged.columns and "y_true" not in merged.columns:
        merged = merged.rename(columns={"wealth_index": "y_true"})
    merged["uncertainty_half_width"] = (merged["upper_90"] - merged["lower_90"]) / 2.0
    return merged


def plot_cluster_choropleth(
    gdf: gpd.GeoDataFrame,
    column: str,
    out_path: Path,
    *,
    title: str,
    cmap: str = "RdYlBu_r",
    vmin: float | None = None,
    vmax: float | None = None,
    add_cities: bool = True,
) -> None:
    """Carte choroplèthe sur buffers de grappes."""
    fig, ax = plt.subplots(figsize=(10, 11))
    plot_gdf = gdf.to_crs(_WGS84)
    plot_gdf.plot(
        column=column,
        ax=ax,
        cmap=cmap,
        legend=True,
        legend_kwds={"label": column, "shrink": 0.6},
        vmin=vmin,
        vmax=vmax,
        edgecolor="#333333",
        linewidth=0.15,
        alpha=0.85,
    )
    if add_cities:
        for name, (lon, lat) in _MAJOR_CITIES.items():
            ax.plot(lon, lat, "k^", ms=5)
            ax.annotate(name, (lon, lat), fontsize=7, ha="left", xytext=(3, 3), textcoords="offset points")
    ax.set_xlim(8.3, 16.5)
    ax.set_ylim(1.5, 13.2)
    ax.set_title(title, fontsize=12)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_regional_maps(
    gdf: gpd.GeoDataFrame,
    column: str,
    regions: list[str],
    out_dir: Path,
    *,
    cmap: str = "RdYlBu_r",
) -> list[Path]:
    """Cartes zoomées par région DHS."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    vmin = gdf[column].quantile(0.05)
    vmax = gdf[column].quantile(0.95)

    for region in regions:
        sub = gdf[gdf["region"] == region]
        if sub.empty:
            continue
        safe = region.replace(" ", "_").replace("é", "e").replace("ô", "o")
        out_path = out_dir / f"regional_{safe}_{column}.png"
        plot_cluster_choropleth(
            sub,
            column,
            out_path,
            title=f"{region} — {column}",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            add_cities=True,
        )
        paths.append(out_path)
    return paths


def interpolate_clusters_to_grid(
    gdf: gpd.GeoDataFrame,
    value_col: str,
    *,
    cell_size_m: float = 1000.0,
    margin_m: float = 5000.0,
    function: str = "multiquadric",
    smooth: float = 0.1,
) -> tuple[np.ndarray, object, str]:
    """
    Interpole les valeurs des grappes (centroïdes) sur une grille régulière 1 km.

    Returns
    -------
    array, transform, crs
    """
    pts = gdf.to_crs(_CAMEROON_CRS)
    minx, miny, maxx, maxy = pts.total_bounds
    minx -= margin_m
    miny -= margin_m
    maxx += margin_m
    maxy += margin_m

    cols = int(np.ceil((maxx - minx) / cell_size_m))
    rows = int(np.ceil((maxy - miny) / cell_size_m))
    xs = minx + (np.arange(cols) + 0.5) * cell_size_m
    ys = maxy - (np.arange(rows) + 0.5) * cell_size_m
    grid_x, grid_y = np.meshgrid(xs, ys)

    cx = pts.geometry.centroid.x.to_numpy()
    cy = pts.geometry.centroid.y.to_numpy()
    values = pts[value_col].to_numpy(dtype=float)

    rbf = Rbf(cx, cy, values, function=function, smooth=smooth)
    grid_z = rbf(grid_x, grid_y)

    # Masque grossier : bbox Cameroun en UTM
    from rasterio.transform import from_origin
    transform = from_origin(minx, maxy, cell_size_m, cell_size_m)
    return grid_z.astype(np.float32), transform, _CAMEROON_CRS


def export_interpolated_raster(
    gdf: gpd.GeoDataFrame,
    value_col: str,
    out_path: Path,
    *,
    nodata: float = -9999.0,
) -> Path:
    """Exporte une grille interpolée 1 km en GeoTIFF."""
    arr, transform, crs = interpolate_clusters_to_grid(gdf, value_col)
    arr = np.where(np.isfinite(arr), arr, nodata)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    array_to_geotiff(arr, str(out_path), transform, crs=crs, nodata=nodata)
    return out_path


def plot_raster_preview(
    raster_path: Path,
    out_path: Path,
    *,
    title: str,
    cmap: str = "RdYlBu_r",
    colorbar_label: str = "Wealth index (hv271)",
    vmin: float | None = None,
    vmax: float | None = None,
    add_cities: bool = True,
    add_scale: bool = True,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
) -> None:
    """Aperçu PNG géoréférencé d'un GeoTIFF (légende, échelle approximative)."""
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata
        if nodata is not None:
            data = np.ma.masked_equal(data, nodata)
        bounds = transform_bounds(src.crs, _WGS84, *src.bounds)
        extent = (bounds[0], bounds[2], bounds[1], bounds[3])

    if vmin is None or vmax is None:
        valid = data.compressed() if np.ma.isMaskedArray(data) else data[np.isfinite(data)]
        if len(valid):
            vmin = vmin if vmin is not None else float(np.percentile(valid, 2))
            vmax = vmax if vmax is not None else float(np.percentile(valid, 98))

    fig, ax = plt.subplots(figsize=(10, 11))
    im = ax.imshow(
        data,
        cmap=cmap,
        origin="upper",
        extent=extent,
        vmin=vmin,
        vmax=vmax,
    )
    cbar = plt.colorbar(im, ax=ax, shrink=0.55, pad=0.02)
    cbar.set_label(colorbar_label)
    ax.set_xlim(xlim if xlim else (8.3, 16.5))
    ax.set_ylim(ylim if ylim else (1.5, 13.2))
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_title(title, fontsize=12)
    ax.set_aspect("equal")

    if add_cities:
        for name, (lon, lat) in _MAJOR_CITIES.items():
            ax.plot(lon, lat, "k^", ms=5, zorder=5)
            ax.annotate(
                name, (lon, lat), fontsize=7, ha="left",
                xytext=(3, 3), textcoords="offset points", zorder=5,
            )

    if add_scale:
        scale_km = 200
        scale_deg = scale_km / 111.0
        x0, y0 = 9.0, 2.2
        ax.plot([x0, x0 + scale_deg], [y0, y0], "k-", lw=2)
        ax.text(x0 + scale_deg / 2, y0 + 0.15, f"{scale_km} km", ha="center", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_regional_raster_maps(
    raster_path: Path,
    clusters_gdf: gpd.GeoDataFrame,
    regions: list[str],
    out_dir: Path,
    *,
    title_template: str = "{region} — wealth index estimé (v4, 1 km)",
    cmap: str = "RdYlBu_r",
    colorbar_label: str = "Wealth index (hv271)",
) -> list[Path]:
    """Cartes raster zoomées par région DHS (étendue des grappes + marge)."""
    import rasterio

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    with rasterio.open(raster_path) as src:
        data_all = src.read(1)
        nodata = src.nodata if src.nodata is not None else -9999.0
        valid = data_all[data_all != nodata]
        vmin = float(np.percentile(valid, 2)) if len(valid) else None
        vmax = float(np.percentile(valid, 98)) if len(valid) else None

        for region in regions:
            sub = clusters_gdf[clusters_gdf["region"] == region]
            if sub.empty:
                continue
            sub_wgs = sub.to_crs(_WGS84)
            minx, miny, maxx, maxy = sub_wgs.total_bounds
            margin = 0.4
            minx -= margin
            miny -= margin
            maxx += margin
            maxy += margin

            safe = region.replace(" ", "_").replace("é", "e").replace("ô", "o").replace("è", "e")
            out_path = out_dir / f"regional_{safe}_raster_v4.png"
            plot_raster_preview(
                raster_path,
                out_path,
                title=title_template.format(region=region),
                cmap=cmap,
                colorbar_label=colorbar_label,
                vmin=vmin,
                vmax=vmax,
                xlim=(minx, maxx),
                ylim=(miny, maxy),
                add_scale=False,
            )
            paths.append(out_path)

    return paths