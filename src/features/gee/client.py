"""
Initialisation du client Google Earth Engine et helpers de session.
"""

from __future__ import annotations

from typing import Any

import ee

from src.features.gee.config import load_gee_config


def require_project_id(config: dict[str, Any]) -> str:
    """
    Retourne le project_id GEE ou lève une erreur explicite.

    Parameters
    ----------
    config : dict
        Section `gee` de configs/gee.yaml.

    Returns
    -------
    str
        Identifiant du projet Google Cloud / Earth Engine.
    """
    project_id = config.get("project_id")
    if not project_id:
        raise ValueError(
            "gee.project_id est requis dans configs/gee.yaml "
            '(ex. project_id: "cameroon-poverty-mapping").'
        )
    return str(project_id)


def initialize_gee(project_id: str | None = None, *, quiet: bool = False) -> ee:
    """
    Initialise Earth Engine et retourne le module `ee`.

    Depuis 2024+, un `project_id` Google Cloud est généralement requis.
    Utilisez ``ee.Initialize(project=project_id)`` lorsque le projet est connu.

    Parameters
    ----------
    project_id : str, optional
        Identifiant du projet Google Cloud / Earth Engine.
    quiet : bool, default False
        Si True, n'affiche pas le message de succès.

    Returns
    -------
    module
        Module `ee` initialisé.

    Raises
    ------
    RuntimeError
        Si l'authentification ou l'initialisation échoue.

    Examples
    --------
    >>> from src.features.gee.config import load_gee_config
    >>> cfg = load_gee_config()
    >>> ee = initialize_gee(project_id=require_project_id(cfg))
    """
    try:
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
    except Exception as exc:
        raise RuntimeError(
            "Échec d'initialisation GEE.\n"
            "1. Exécutez : earthengine authenticate\n"
            "2. Définissez gee.project_id dans configs/gee.yaml\n"
            f"Erreur d'origine : {exc}"
        ) from exc

    if not quiet:
        label = project_id or "(projet par défaut)"
        print(f"Google Earth Engine initialisé avec succès — projet : {label}")
    return ee


def initialize_from_config(
    config_path: str | None = None,
    *,
    quiet: bool = False,
) -> tuple[ee, dict[str, Any]]:
    """
    Charge la config GEE, initialise le client et retourne (ee, config).

    Parameters
    ----------
    config_path : str, optional
        Chemin vers configs/gee.yaml. Par défaut : fichier à la racine du projet.
    quiet : bool, default False
        Passe ``quiet=True`` à ``initialize_gee``.

    Returns
    -------
    tuple
        (module ee initialisé, dictionnaire de configuration)
    """
    config = load_gee_config(config_path)
    project_id = require_project_id(config)
    return initialize_gee(project_id=project_id, quiet=quiet), config


def get_test_aoi(config: dict[str, Any]) -> ee.Geometry:
    """
    Retourne la géométrie de test (bbox Yaoundé par défaut).

    Parameters
    ----------
    config : dict
        Section `gee` de configs/gee.yaml.

    Returns
    -------
    ee.Geometry
        Rectangle [W, S, E, N] défini dans ``test_aoi.bbox``.
    """
    west, south, east, north = config["test_aoi"]["bbox"]
    return ee.Geometry.Rectangle([west, south, east, north])