"""Raster → aligned float32 arrays, PNG overlays, WGS84 bounds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine, array_bounds
from rasterio.warp import Resampling, reproject, transform_bounds

from src.partner_web import EXIT_CRS, EXIT_EMPTY_UNCERTAINTY, EXIT_MISSING_RASTER, EXIT_PAYLOAD

SOFT_MB = 8.0
HARD_MB = 12.0
MAX_EDGE = 2048


class RenderError(Exception):
    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


@dataclass
class LayerStack:
    wealth: np.ndarray
    priority: np.ndarray
    uncertainty: np.ndarray
    transform: Affine
    crs: CRS
    bounds_wgs84: dict[str, float]
    wealth_path: str
    shapes: dict[str, list[int]]


def _open_profile(path: Path) -> tuple[Any, dict]:
    if not path.is_file():
        raise RenderError(f"raster missing: {path}", EXIT_MISSING_RASTER)
    try:
        ds = rasterio.open(path)
    except Exception as exc:  # noqa: BLE001 — surface as exit 2
        raise RenderError(f"cannot open raster {path}: {exc}", EXIT_MISSING_RASTER) from exc
    return ds, dict(ds.profile)


def _target_shape(height: int, width: int, max_edge: int = MAX_EDGE) -> tuple[int, int]:
    m = max(height, width)
    if m <= max_edge:
        return height, width
    scale = max_edge / float(m)
    return max(1, int(round(height * scale))), max(1, int(round(width * scale)))


def _scaled_transform(transform: Affine, src_h: int, src_w: int, dst_h: int, dst_w: int) -> Affine:
    if src_h == dst_h and src_w == dst_w:
        return transform
    sx = src_w / dst_w
    sy = src_h / dst_h
    return Affine(transform.a * sx, transform.b, transform.c, transform.d, transform.e * sy, transform.f)


def warp_to_master(
    src_path: Path,
    master_transform: Affine,
    master_crs: CRS,
    out_h: int,
    out_w: int,
    *,
    resampling: Resampling = Resampling.bilinear,
    nodata_fill: float = np.nan,
) -> np.ndarray:
    """Reproject src into master grid as float32 (out_h, out_w)."""
    try:
        with rasterio.open(src_path) as src:
            dst = np.full((out_h, out_w), nodata_fill, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=dst,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata,
                dst_transform=master_transform,
                dst_crs=master_crs,
                dst_nodata=np.nan,
                resampling=resampling,
            )
            return dst
    except Exception as exc:  # noqa: BLE001
        raise RenderError(f"reproject failed for {src_path}: {exc}", EXIT_CRS) from exc


def load_master_wealth(path: Path, max_edge: int = MAX_EDGE) -> tuple[np.ndarray, Affine, CRS]:
    ds, _ = _open_profile(path)
    try:
        if ds.crs is None:
            raise RenderError(f"wealth raster has no CRS: {path}", EXIT_CRS)
        data = ds.read(1, out_dtype=np.float32)
        if ds.nodata is not None:
            data = np.where(data == ds.nodata, np.nan, data)
        th, tw = _target_shape(ds.height, ds.width, max_edge)
        if (th, tw) != (ds.height, ds.width):
            # reproject onto coarser grid in same CRS
            dst = np.full((th, tw), np.nan, dtype=np.float32)
            dst_transform = _scaled_transform(ds.transform, ds.height, ds.width, th, tw)
            reproject(
                source=data,
                destination=dst,
                src_transform=ds.transform,
                src_crs=ds.crs,
                dst_transform=dst_transform,
                dst_crs=ds.crs,
                src_nodata=np.nan,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            return dst, dst_transform, ds.crs
        return data, ds.transform, ds.crs
    except RenderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RenderError(f"wealth load failed: {exc}", EXIT_CRS) from exc
    finally:
        ds.close()


def is_empty_layer(arr: np.ndarray) -> bool:
    finite = np.isfinite(arr)
    return int(finite.sum()) == 0


def bounds_wgs84(transform: Affine, height: int, width: int, crs: CRS) -> dict[str, float]:
    left, bottom, right, top = array_bounds(height, width, transform)
    try:
        w, s, e, n = transform_bounds(crs, CRS.from_epsg(4326), left, bottom, right, top, densify_pts=21)
    except Exception as exc:  # noqa: BLE001
        raise RenderError(f"bounds to WGS84 failed: {exc}", EXIT_CRS) from exc
    return {"west": float(w), "south": float(s), "east": float(e), "north": float(n)}


def build_layer_stack(
    wealth_path: Path,
    priority_path: Path,
    uncertainty_path: Path,
    *,
    max_edge: int = MAX_EDGE,
) -> LayerStack:
    wealth, transform, crs = load_master_wealth(wealth_path, max_edge=max_edge)
    h, w = wealth.shape

    if not priority_path.is_file():
        raise RenderError(f"priority missing: {priority_path}", EXIT_MISSING_RASTER)
    if not uncertainty_path.is_file():
        raise RenderError(f"uncertainty missing: {uncertainty_path}", EXIT_EMPTY_UNCERTAINTY)

    priority = warp_to_master(
        priority_path, transform, crs, h, w, resampling=Resampling.bilinear
    )
    uncertainty = warp_to_master(
        uncertainty_path, transform, crs, h, w, resampling=Resampling.bilinear
    )
    if is_empty_layer(uncertainty):
        raise RenderError("uncertainty empty (no finite pixels)", EXIT_EMPTY_UNCERTAINTY)

    # alignment self-check
    if priority.shape != wealth.shape or uncertainty.shape != wealth.shape:
        raise RenderError("post-warp shape mismatch", EXIT_CRS)

    b = bounds_wgs84(transform, h, w, crs)
    return LayerStack(
        wealth=wealth,
        priority=priority,
        uncertainty=uncertainty,
        transform=transform,
        crs=crs,
        bounds_wgs84=b,
        wealth_path=str(wealth_path.as_posix()),
        shapes={"wealth": list(wealth.shape), "priority": list(priority.shape), "uncertainty": list(uncertainty.shape)},
    )


def _percentile_limits(arr: np.ndarray, lo: float = 2.0, hi: float = 98.0) -> tuple[float, float]:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin, vmax = np.percentile(finite, [lo, hi])
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.nanmin(finite))
        vmax = float(np.nanmax(finite))
        if vmin == vmax:
            vmax = vmin + 1.0
    return float(vmin), float(vmax)


def array_to_png(
    arr: np.ndarray,
    out_path: Path,
    *,
    cmap: str = "YlOrRd",
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """Write single-band float array to RGBA PNG (transparent nodata)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = np.array(arr, dtype=np.float64, copy=True)
    mask = ~np.isfinite(data)
    if vmin is None or vmax is None:
        pmin, pmax = _percentile_limits(data)
        vmin = pmin if vmin is None else vmin
        vmax = pmax if vmax is None else vmax
    norm = plt.Normalize(vmin=vmin, vmax=vmax, clip=True)
    rgba = plt.get_cmap(cmap)(norm(np.ma.array(data, mask=mask)))
    rgba = np.asarray(rgba)
    rgba[mask, 3] = 0.0
    plt.imsave(out_path, rgba, format="png")


def write_layer_pngs(stack: LayerStack, assets_dir: Path) -> dict[str, Path]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "wealth": assets_dir / "wealth.png",
        "priority": assets_dir / "priority.png",
        "uncertainty": assets_dir / "uncertainty.png",
    }
    array_to_png(stack.wealth, paths["wealth"], cmap="YlOrRd")
    array_to_png(stack.priority, paths["priority"], cmap="Purples")
    array_to_png(stack.uncertainty, paths["uncertainty"], cmap="Blues")
    bounds_path = assets_dir / "bounds.json"
    bounds_path.write_text(json.dumps(stack.bounds_wgs84, indent=2), encoding="utf-8")
    return paths


def total_assets_mb(paths: list[Path]) -> float:
    return sum(p.stat().st_size for p in paths if p.is_file()) / (1024 * 1024)


def enforce_payload_budget(site_dir: Path, hard_mb: float = HARD_MB) -> float:
    assets = list((site_dir / "assets").glob("*")) if (site_dir / "assets").is_dir() else []
    mb = total_assets_mb(assets)
    if mb > hard_mb:
        raise RenderError(f"overview assets {mb:.2f} MB exceed hard budget {hard_mb} MB", EXIT_PAYLOAD)
    return mb
