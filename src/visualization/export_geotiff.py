"""
Fonctions pour exporter des résultats en GeoTIFF.
"""

import rasterio
from rasterio.transform import from_origin
import numpy as np


def array_to_geotiff(
    array: np.ndarray,
    output_path: str,
    transform,
    crs="EPSG:4326",
    nodata=None
):
    """
    Exporte un tableau numpy en fichier GeoTIFF.
    """
    height, width = array.shape
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=array.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata
    ) as dst:
        dst.write(array, 1)