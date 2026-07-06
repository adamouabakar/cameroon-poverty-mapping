"""
Distances aux infrastructures via Google Earth Engine.

Sources (configs/gee.yaml) :
  - routes   : GRIP4/Africa
  - santé    : Global Healthsites (node + way)
  - écoles   : asset GEE et/ou GeoJSON local HOT/OSM Cameroun

La source écoles par défaut utilise le jeu HOT HDX (10 200 établissements OSM)
converti en points pour des distances réalistes.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import ee
import geopandas as gpd

from src.features.gee.projection import reproject_to_target
from src.utils.helpers import get_project_root


def _fc_to_distance_m(
    fc: ee.FeatureCollection,
    aoi: ee.Geometry,
    scale: int,
    max_distance_m: int,
    band_name: str,
) -> ee.Image:
    """
    Rasterise une FeatureCollection et calcule la distance euclidienne (m).

    Si la collection est vide, retourne une image constante au plafond.
    """
    empty = fc.size().eq(0)

    painted = (
        ee.Image(0)
        .byte()
        .paint(fc, 1)
        .unmask(0)
        .clip(aoi)
    )

    distance = (
        painted.fastDistanceTransform(neighborhood=256, units="pixels")
        .sqrt()
        .multiply(scale)
        .min(ee.Image(max_distance_m))
        .rename(band_name)
    )

    fallback = ee.Image(max_distance_m).rename(band_name).clip(aoi)
    return ee.Image(ee.Algorithms.If(empty, fallback, distance))


def _load_fc(asset: str | None, aoi: ee.Geometry) -> ee.FeatureCollection:
    """Charge une FeatureCollection GEE si l'asset est défini."""
    if not asset:
        return ee.FeatureCollection([])
    return ee.FeatureCollection(asset).filterBounds(aoi)


@lru_cache(maxsize=1)
def _load_local_schools_fc(geojson_path: str) -> ee.FeatureCollection:
    """
    Charge les écoles HOT/OSM depuis un GeoJSON local (points).

    Le fichier est sérialisé une fois dans le graphe EE ; utiliser la version
    points préparée par ``scripts/prepare_hotosm_schools.py``.
    """
    path = Path(geojson_path)
    if not path.is_absolute():
        path = get_project_root() / path
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON écoles introuvable : {path}")

    geojson = json.loads(path.read_text(encoding="utf-8"))
    return ee.FeatureCollection(geojson["features"])


def _filter_by_tags(
    fc: ee.FeatureCollection,
    config: dict,
    tag_key: str,
    tags: list[str],
) -> ee.FeatureCollection:
    """Filtre une FC sur une propriété OSM (amenity, building, fclass...)."""
    if not tags:
        return fc
    prop = config["osm"].get(tag_key, config["osm"].get("feature_property", "amenity"))
    return fc.filter(ee.Filter.inList(prop, tags))


def get_roads_fc(aoi: ee.Geometry, config: dict) -> ee.FeatureCollection:
    """FeatureCollection des routes intersectant l'AOI (GRIP4 par défaut)."""
    return _load_fc(config["osm"]["roads"], aoi)


def get_health_fc(aoi: ee.Geometry, config: dict) -> ee.FeatureCollection:
    """Fusionne les sources santé (points + polygones) et filtre par tags."""
    osm_cfg = config["osm"]
    health_tags = osm_cfg["health_tags"]

    sources = []
    for key in ("health_nodes", "health_ways"):
        asset = osm_cfg.get(key)
        if asset:
            sources.append(_load_fc(asset, aoi))

    if not sources:
        return ee.FeatureCollection([])

    merged = sources[0]
    for extra in sources[1:]:
        merged = merged.merge(extra)

    prop = osm_cfg.get("health_property", "healthcare")
    amenity_prop = osm_cfg.get("feature_property", "amenity")

    by_healthcare = ee.Filter.inList(prop, health_tags)
    by_amenity = ee.Filter.inList(amenity_prop, health_tags)
    return merged.filter(by_healthcare.Or(by_amenity))


def get_schools_fc(aoi: ee.Geometry, config: dict) -> ee.FeatureCollection:
    """
    FeatureCollection des écoles pour le calcul de ``dist_school_m``.

    Priorité :
    1. ``schools_local_geojson`` (HOT/OSM Cameroun — recommandé)
    2. ``schools`` asset GEE (si configuré)
    """
    osm_cfg = config["osm"]
    amenity_tags = osm_cfg.get("school_amenity_tags", osm_cfg.get("school_tags", []))
    building_tags = osm_cfg.get("school_building_tags", [])

    local_path = osm_cfg.get("schools_local_geojson")
    if local_path:
        # Fichier HOT pré-filtré par prepare_hotosm_schools.py
        return _load_local_schools_fc(str(local_path)).filterBounds(aoi)

    asset = osm_cfg.get("schools")
    if not asset:
        return ee.FeatureCollection([])

    fc = _load_fc(asset, aoi)
    fc_amenity = _filter_by_tags(fc, config, "school_amenity_property", amenity_tags)
    if building_tags:
        fc_building = _filter_by_tags(fc, config, "school_building_property", building_tags)
        return fc_amenity.merge(fc_building).distinct()
    return fc_amenity


def get_osm_distances(aoi: ee.Geometry, config: dict) -> ee.Image:
    """
    Produit les trois bandes de distance reprojetées à export_scale.

    Returns
    -------
    ee.Image
        Bandes : dist_road_m, dist_school_m, dist_health_m
    """
    osm_cfg = config["osm"]
    scale = int(config["export_scale"])
    max_dist = int(osm_cfg.get("max_distance_m", 50000))

    roads_fc = get_roads_fc(aoi, config)
    schools_fc = get_schools_fc(aoi, config)
    health_fc = get_health_fc(aoi, config)

    dist_road = _fc_to_distance_m(roads_fc, aoi, scale, max_dist, "dist_road_m")
    dist_school = _fc_to_distance_m(schools_fc, aoi, scale, max_dist, "dist_school_m")
    dist_health = _fc_to_distance_m(health_fc, aoi, scale, max_dist, "dist_health_m")

    stacked = dist_road.addBands([dist_school, dist_health])
    return reproject_to_target(stacked, config)