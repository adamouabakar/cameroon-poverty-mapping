"""
Simulation du déplacement géographique (jitter) des grappes DHS.

Référence : politique de confidentialité GPS du programme DHS
(https://dhsprogram.com/methodology/GPS-Data-Dissemination.cfm) :
  - Zones urbaines  : déplacement aléatoire de 0 à 2 km
  - Zones rurales   : déplacement aléatoire de 0 à 5 km
  - 1 % des grappes : déplacement jusqu'à 10 km (toutes zones confondues)

Les coordonnées publiées dans les fichiers GE DHS sont déjà jitterées.
Cette simulation s'applique aux coordonnées « réelles » (non publiées) ou
lorsqu'on souhaite reproduire la politique DHS à partir de points exacts.
"""

from __future__ import annotations

import numpy as np
import geopandas as gpd
import pandas as pd

# Rayons officiels (km)
URBAN_JITTER_KM = 2.0
RURAL_JITTER_KM = 5.0
EXTENDED_JITTER_KM = 10.0
EXTENDED_FRACTION = 0.01

# UTM zone 33N — projection métrique adaptée au Cameroun
_CAMEROON_UTM = "EPSG:32633"
_WGS84 = "EPSG:4326"


def _max_jitter_km(
    urban_rural: str,
    is_extended: bool,
    *,
    urban_km: float = URBAN_JITTER_KM,
    rural_km: float = RURAL_JITTER_KM,
    extended_km: float = EXTENDED_JITTER_KM,
) -> float:
    """Retourne le rayon maximal de jitter applicable à une grappe."""
    if is_extended:
        return extended_km
    return urban_km if urban_rural == "urban" else rural_km


def _draw_jitter_distances_km(
    n: int,
    urban_rural: pd.Series,
    rng: np.random.Generator,
    *,
    urban_km: float = URBAN_JITTER_KM,
    rural_km: float = RURAL_JITTER_KM,
    extended_km: float = EXTENDED_JITTER_KM,
    extended_fraction: float = EXTENDED_FRACTION,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Tire les distances de jitter pour chaque grappe.

    - Distance uniforme dans [0, rayon_max] (loi usuelle en cartographie DHS).
    - 1 % des grappes reçoivent le rayon étendu (10 km), indépendamment
      du type urbain/rural.
    """
    is_extended = rng.random(n) < extended_fraction
    max_km = np.array(
        [
            _max_jitter_km(ur, ext, urban_km=urban_km, rural_km=rural_km, extended_km=extended_km)
            for ur, ext in zip(urban_rural, is_extended)
        ],
        dtype=float,
    )
    # Distance uniforme sur le segment [0, max] — pas sur le disque (sqrt)
    distances = rng.uniform(0.0, 1.0, size=n) * max_km
    return distances, is_extended


def simulate_dhs_jitter(
    gdf: gpd.GeoDataFrame,
    *,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    urban_rural_col: str = "urban_rural",
    random_state: int | None = 42,
    urban_km: float = URBAN_JITTER_KM,
    rural_km: float = RURAL_JITTER_KM,
    extended_km: float = EXTENDED_JITTER_KM,
    extended_fraction: float = EXTENDED_FRACTION,
    inplace: bool = False,
) -> gpd.GeoDataFrame:
    """
    Applique un déplacement aléatoire aux coordonnées de chaque grappe.

    Les coordonnées d'entrée (lon_col, lat_col) sont considérées comme
    « réelles ». Elles ne sont jamais conservées dans la sortie : seules
    les positions jitterées sont exposées.

    Parameters
    ----------
    gdf : GeoDataFrame avec colonnes lon/lat et urban_rural.
    random_state : graine pour reproductibilité (None = tirage non déterministe).

    Returns
    -------
    GeoDataFrame avec latitude, longitude et geometry mis à jour, plus
    jitter_distance_km et jitter_extended (métadonnées de traçabilité).
    """
    if lon_col not in gdf.columns or lat_col not in gdf.columns:
        raise KeyError(f"Colonnes requises manquantes : {lon_col}, {lat_col}")
    if urban_rural_col not in gdf.columns:
        raise KeyError(f"Colonne urbain/rural manquante : {urban_rural_col}")

    out = gdf if inplace else gdf.copy()
    rng = np.random.default_rng(random_state)
    n = len(out)

    distances_km, is_extended = _draw_jitter_distances_km(
        n,
        out[urban_rural_col],
        rng,
        urban_km=urban_km,
        rural_km=rural_km,
        extended_km=extended_km,
        extended_fraction=extended_fraction,
    )
    # Bearing uniforme [0, 360°)
    bearings_deg = rng.uniform(0.0, 360.0, size=n)

    # Projection locale en mètres pour un déplacement euclidien fiable
    points = gpd.GeoDataFrame(
        out[[urban_rural_col]],
        geometry=gpd.points_from_xy(out[lon_col], out[lat_col]),
        crs=_WGS84,
    ).to_crs(_CAMEROON_UTM)

    bearings_rad = np.radians(bearings_deg)
    offset_m = distances_km * 1000.0
    dx = offset_m * np.sin(bearings_rad)
    dy = offset_m * np.cos(bearings_rad)

    jittered = points.copy()
    jittered["geometry"] = gpd.points_from_xy(
        points.geometry.x + dx,
        points.geometry.y + dy,
        crs=_CAMEROON_UTM,
    )
    jittered_wgs = jittered.to_crs(_WGS84)

    out["latitude"] = jittered_wgs.geometry.y
    out["longitude"] = jittered_wgs.geometry.x
    out["geometry"] = jittered_wgs.geometry
    out["jitter_distance_km"] = distances_km
    out["jitter_extended"] = is_extended

    # Supprimer d'éventuelles colonnes de coordonnées brutes
    for raw_col in ("latitude_raw", "longitude_raw"):
        if raw_col in out.columns:
            out = out.drop(columns=[raw_col])

    return out


def validate_buffer_covers_jitter(
    buffer_km: pd.Series,
    jitter_distance_km: pd.Series,
) -> None:
    """
    Vérifie que chaque buffer englobe le jitter simulé (buffer_km >= jitter).

    À appeler après create_cluster_buffers() pour garantir la cohérence
    méthodologique buffer / incertitude de localisation.
    """
    violations = buffer_km < jitter_distance_km
    if violations.any():
        n = int(violations.sum())
        worst = (jitter_distance_km - buffer_km).max()
        raise ValueError(
            f"{n} grappe(s) ont un buffer plus petit que le jitter simulé "
            f"(écart max : {worst:.2f} km)."
        )