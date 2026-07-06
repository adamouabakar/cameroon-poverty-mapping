"""Définition des zones d'étude (AOI)."""

from __future__ import annotations

import ee


def get_cameroon_geometry(config: dict) -> ee.Geometry:
    """Retourne la géométrie du Cameroun via LSIB."""
    aoi_cfg = config["aoi"]
    countries = ee.FeatureCollection(aoi_cfg["country_asset"])
    cameroon = countries.filter(
        ee.Filter.eq(aoi_cfg["country_filter_property"], aoi_cfg["country_filter_value"])
    )
    return cameroon.geometry()


def get_test_bbox_geometry(config: dict) -> ee.Geometry:
    """Retourne la bbox de test (Yaoundé par défaut)."""
    west, south, east, north = config["test_aoi"]["bbox"]
    return ee.Geometry.Rectangle([west, south, east, north])


def get_aoi_geometry(config: dict, mode: str = "test") -> ee.Geometry:
    """Retourne l'AOI selon le mode (`test` ou `national`)."""
    if mode == "national":
        return get_cameroon_geometry(config)
    if mode == "test":
        return get_test_bbox_geometry(config)
    raise ValueError(f"Mode AOI inconnu : {mode}")