"""Conversion des grappes DHS en FeatureCollection Earth Engine."""

from __future__ import annotations

import json

import ee
import geopandas as gpd


def gdf_to_ee_fc(gdf: gpd.GeoDataFrame) -> ee.FeatureCollection:
    """Convertit un GeoDataFrame (buffers ou points) en ee.FeatureCollection."""
    gdf = gdf.to_crs(epsg=4326)
    keep_cols = [
        c
        for c in ["cluster_id", "urban_rural", "region", "buffer_km"]
        if c in gdf.columns
    ]
    slim = gdf[keep_cols + ["geometry"]].copy()
    geojson = json.loads(slim.to_json())
    return ee.FeatureCollection(geojson["features"])