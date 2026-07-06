"""
Fonctions utilitaires spécifiques à Google Earth Engine.
"""

import ee


def initialize_gee():
    """Initialise Google Earth Engine."""
    try:
        ee.Initialize()
        print("Google Earth Engine initialisé avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de GEE: {e}")


def get_sentinel2_collection(start_date: str, end_date: str, cloud_cover: int = 20):
    """Retourne une collection Sentinel-2 filtrée."""
    return (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)))