"""Tests configuration écoles OSM/HOT."""

from pathlib import Path

from src.features.gee.config import load_gee_config


def test_schools_local_geojson_configured():
    config = load_gee_config()
    path = config["osm"].get("schools_local_geojson")
    assert path, "schools_local_geojson doit être défini"
    full = Path(__file__).resolve().parent.parent / path
    assert full.exists(), f"Fichier écoles manquant : {full}"


def test_schools_geojson_has_education_points():
    import geopandas as gpd

    config = load_gee_config()
    path = Path(__file__).resolve().parent.parent / config["osm"]["schools_local_geojson"]
    gdf = gpd.read_file(path)
    assert len(gdf) > 5000
    assert "amenity" in gdf.columns or "building" in gdf.columns