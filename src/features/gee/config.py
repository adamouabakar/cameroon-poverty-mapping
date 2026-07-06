"""
Chargement et validation de la configuration GEE.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.features.gee.composites.chirps import CHIRPS_FEATURE_COLUMNS
from src.utils.helpers import get_project_root

REQUIRED_TOP_LEVEL_KEYS = [
    "export_scale",
    "crs",
    "temporal",
    "sentinel2",
    "viirs",
    "dem",
    "worldpop",
    "landcover",
    "ghsl",
    "chirps",
    "osm",
    "test_aoi",
    "feature_columns",
    "band_names",
]

VALID_FEATURE_SETS = ("v1", "v2", "v3")


def load_gee_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Charge `configs/gee.yaml` et retourne la section `gee`.

    Parameters
    ----------
    config_path : str | Path, optional
        Chemin vers le fichier YAML. Par défaut : configs/gee.yaml à la racine.

    Returns
    -------
    dict
        Dictionnaire de configuration GEE validé.

    Raises
    ------
    FileNotFoundError
        Si le fichier de configuration est introuvable.
    ValueError
        Si des clés obligatoires sont manquantes.
    """
    if config_path is None:
        config_path = get_project_root() / "configs" / "gee.yaml"
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration GEE introuvable : {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = raw.get("gee")
    if config is None:
        raise ValueError(f"Section 'gee' absente dans {config_path}")

    # Colonnes v1 de référence (racine YAML) — conservées pour la rétrocompatibilité
    config["_base_feature_columns"] = list(config["feature_columns"])
    config["_base_band_names"] = dict(config["band_names"])

    config = resolve_feature_set(config)
    validate_gee_config(config)
    return config


def resolve_feature_set(config: dict[str, Any]) -> dict[str, Any]:
    """
    Applique les overrides de feature_columns / band_names selon feature_set.

    v1 utilise les colonnes définies au niveau racine de la section gee.
    v2/v3 remplacent par le bloc feature_sets.<version>.
    """
    resolved = dict(config)
    feature_set = resolved.get("feature_set", "v1")
    if feature_set not in VALID_FEATURE_SETS:
        raise ValueError(
            f"feature_set invalide : {feature_set!r}. "
            f"Valeurs acceptées : {VALID_FEATURE_SETS}"
        )

    # Toujours repartir des colonnes v1 (racine YAML)
    resolved["feature_columns"] = list(
        config.get("_base_feature_columns", config["feature_columns"])
    )
    resolved["band_names"] = dict(
        config.get("_base_band_names", config["band_names"])
    )

    if feature_set != "v1":
        overrides = resolved.get("feature_sets", {}).get(feature_set, {})
        if "feature_columns" in overrides:
            resolved["feature_columns"] = list(overrides["feature_columns"])
        if "band_names" in overrides:
            resolved["band_names"] = dict(overrides["band_names"])

    return resolved


def get_feature_set(config: dict[str, Any]) -> str:
    """Retourne la version active du jeu de features (v1 par défaut)."""
    return str(config.get("feature_set", "v1"))


def validate_gee_config(config: dict[str, Any]) -> None:
    """Vérifie la présence des clés obligatoires et quelques contraintes simples."""
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in config]
    if missing:
        raise ValueError(f"Clés manquantes dans configs/gee.yaml : {missing}")

    if config["export_scale"] <= 0:
        raise ValueError("export_scale doit être > 0.")

    if len(config["feature_columns"]) != len(set(config["feature_columns"])):
        raise ValueError("feature_columns contient des doublons.")

    for col in config["feature_columns"]:
        if col not in config["band_names"]:
            raise ValueError(f"band_names ne mappe pas la colonne : {col}")

    feature_set = config.get("feature_set", "v1")
    feature_cols = set(config["feature_columns"])
    chirps_cols = CHIRPS_FEATURE_COLUMNS & feature_cols

    if feature_set == "v2" and "ghsl_built_fraction" not in feature_cols:
        raise ValueError("feature_set v2 requiert la colonne ghsl_built_fraction.")
    if feature_set == "v1" and "ghsl_built_fraction" in feature_cols:
        raise ValueError("ghsl_built_fraction est réservé à feature_set v2+.")
    if feature_set == "v3":
        if "ghsl_built_fraction" not in feature_cols:
            raise ValueError("feature_set v3 requiert ghsl_built_fraction.")
        if chirps_cols != CHIRPS_FEATURE_COLUMNS:
            missing = sorted(CHIRPS_FEATURE_COLUMNS - feature_cols)
            raise ValueError(f"feature_set v3 requiert les colonnes CHIRPS : {missing}")
    if feature_set in ("v1", "v2") and chirps_cols:
        raise ValueError(
            f"Colonnes CHIRPS réservées à feature_set v3 : {sorted(chirps_cols)}"
        )


def get_scale(config: dict[str, Any]) -> int:
    """Retourne la résolution d'extraction en mètres."""
    return int(config["export_scale"])


def get_crs(config: dict[str, Any]) -> str:
    """Retourne le CRS cible (ex. EPSG:32633)."""
    return str(config["crs"])


def get_test_bbox(config: dict[str, Any]) -> list[float]:
    """Retourne la bbox de test [W, S, E, N]."""
    return list(config["test_aoi"]["bbox"])