#!/usr/bin/env python
"""Create tiny GeoTIFF fixtures + metrics JSON for partner_web tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIX = PROJECT_ROOT / "tests" / "fixtures"


def main() -> int:
    FIX.mkdir(parents=True, exist_ok=True)
    # ~Cameroon-ish WGS84 grid (small)
    h, w = 32, 40
    transform = from_origin(9.0, 13.0, 0.05, 0.05)  # west, north, xres, yres
    crs = "EPSG:4326"

    yy, xx = np.mgrid[0:h, 0:w]
    wealth = (xx / w + yy / h).astype(np.float32)
    priority = (1.0 - wealth).astype(np.float32)
    uncertainty = (0.2 + 0.3 * (xx / w)).astype(np.float32)

    # misaligned priority (different transform) to exercise warp
    transform_mis = from_origin(9.02, 13.02, 0.06, 0.06)
    priority_mis = np.linspace(0, 1, 20 * 24, dtype=np.float32).reshape(20, 24)

    def write(path: Path, arr: np.ndarray, transform, crs: str = "EPSG:4326") -> None:
        profile = {
            "driver": "GTiff",
            "height": arr.shape[0],
            "width": arr.shape[1],
            "count": 1,
            "dtype": "float32",
            "crs": crs,
            "transform": transform,
            "nodata": -9999.0,
        }
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(arr, 1)

    write(FIX / "tiny_wealth.tif", wealth, transform)
    write(FIX / "tiny_priority.tif", priority_mis, transform_mis)
    write(FIX / "tiny_uncertainty.tif", uncertainty, transform)
    # empty uncertainty (all nodata)
    empty = np.full((h, w), np.nan, dtype=np.float32)
    write(FIX / "tiny_uncertainty_empty.tif", empty, transform)

    metrics = {
        "n_clusters": 10,
        "cv_strategy": "block",
        "metrics_oof": {"r2": 0.5, "spearman": 0.6, "rmse": 1.0, "mae": 0.8},
    }
    (FIX / "tiny_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote fixtures under {FIX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
