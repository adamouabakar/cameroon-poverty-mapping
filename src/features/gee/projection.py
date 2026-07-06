"""
Utilitaires de reprojection pour aligner les images sur la grille du projet.
"""

from __future__ import annotations

import ee


def reproject_to_target(image: ee.Image, config: dict) -> ee.Image:
    """
    Reprojette une image sur le CRS et la résolution cibles du projet.

    Parameters
    ----------
    image : ee.Image
        Image à reprojeter.
    config : dict
        Section `gee` de configs/gee.yaml.

    Returns
    -------
    ee.Image
        Image reprojetée à `export_scale` mètres en `crs`.
    """
    return image.reproject(crs=config["crs"], scale=config["export_scale"])