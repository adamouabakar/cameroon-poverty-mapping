#!/usr/bin/env python
"""
Prépare les écoles HOT/OSM Cameroun pour le pipeline GEE.

Source : HDX hotosm_cmr_education_facilities (OpenStreetMap, 10 200 entités)
Sortie : points GeoJSON léger (centroïdes) pour ee.FeatureCollection locale.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "data/raw/hotosm/cmr_education_facilities/education_facilities.geojson"
OUTPUT = PROJECT_ROOT / "data/processed/hotosm_cmr_education_points.geojson"

AMENITY_TAGS = {"school", "kindergarten", "college", "university"}
BUILDING_TAGS = {"school", "kindergarten", "college", "university", "education"}
EXCLUDE_AMENITY = {"public_building", "toilets", "place_of_worship", "restaurant", "library", "childcare"}


def prepare_school_points(source: Path = SOURCE, output: Path = OUTPUT) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(source).to_crs(epsg=4326)

    amenity_match = gdf["amenity"].isin(AMENITY_TAGS) if "amenity" in gdf.columns else False
    building_match = gdf["building"].isin(BUILDING_TAGS) if "building" in gdf.columns else False
    education_match = amenity_match | building_match
    if "amenity" in gdf.columns:
        education_match = education_match & ~gdf["amenity"].isin(EXCLUDE_AMENITY)
    gdf = gdf[education_match].copy()

    gdf = gdf.to_crs(epsg=3857)
    gdf["geometry"] = gdf.geometry.centroid
    gdf = gdf.to_crs(epsg=4326)
    keep = [c for c in ["amenity", "building", "name", "adm1_name", "adm2_name"] if c in gdf.columns]
    gdf = gdf[keep + ["geometry"]]

    output.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output, driver="GeoJSON")
    return gdf


def main() -> None:
    gdf = prepare_school_points()
    summary = {
        "n_points": len(gdf),
        "output": str(OUTPUT),
        "amenity_counts": gdf["amenity"].value_counts().head(10).to_dict() if "amenity" in gdf.columns else {},
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()