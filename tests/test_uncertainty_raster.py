import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point

from src.models.uncertainty_raster import _cluster_uncertainty_half_width


def test_cluster_uncertainty_half_width_from_intervals():
    oof = pd.DataFrame({"lower_90": [0.0, 10.0], "upper_90": [2.0, 14.0]})
    hw = _cluster_uncertainty_half_width(oof)
    np.testing.assert_allclose(hw, [1.0, 2.0])


def test_cluster_uncertainty_half_width_explicit_column():
    oof = pd.DataFrame({
        "uncertainty_half_width": [3.5, 4.0],
        "lower_90": [0.0, 1.0],
        "upper_90": [1.0, 2.0],
    })
    hw = _cluster_uncertainty_half_width(oof)
    np.testing.assert_allclose(hw, [3.5, 4.0])