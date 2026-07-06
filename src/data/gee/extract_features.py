"""
DEPRECATED — Utiliser src/features/gee/ à la place.
"""

import warnings

from src.features.gee.extract_clusters import extract_from_clusters_file
from src.features.gee.stack import build_feature_image

warnings.warn(
    "src.data.gee.extract_features est déprécié. "
    "Utilisez src.features.gee ou scripts/extract_gee_features.py.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["build_feature_image", "extract_from_clusters_file"]