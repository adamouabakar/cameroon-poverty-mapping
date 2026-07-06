"""Pipeline d'extraction de features via Google Earth Engine."""

from src.features.gee.client import initialize_gee
from src.features.gee.config import load_gee_config
from src.features.gee.extract_clusters import extract_features_for_clusters
from src.features.gee.stack import build_feature_image

__all__ = [
    "initialize_gee",
    "load_gee_config",
    "build_feature_image",
    "extract_features_for_clusters",
]