"""Generate notebooks/03_gee_feature_extraction.ipynb."""
import json
from pathlib import Path

cells = []


def md(s):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": [s]})


def code(s):
    cells.append(
        {
            "cell_type": "code",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [line + "\n" for line in s.split("\n")],
        }
    )


md(
    """# 03 — Extraction de features Google Earth Engine

**Objectif :** Remplacer les features fictives par des variables réelles extraites via GEE.

> ⚠️ Nécessite un compte Google Earth Engine authentifié et `gee.project_id` dans `configs/gee.yaml`.

**Phase actuelle :** test sur la bbox Yaoundé avant extraction nationale."""
)

code(
    """import json
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.gee.client import initialize_gee
from src.features.gee.config import load_gee_config
from src.features.gee.aoi import get_aoi_geometry
from src.features.gee.stack import build_feature_image
from src.features.gee.extract_clusters import extract_from_clusters_file
from src.utils.helpers import hash_config_file"""
)

code(
    """gee_config = load_gee_config(PROJECT_ROOT / "configs" / "gee.yaml")
initialize_gee(project_id=gee_config.get("project_id"))
print("Config hash:", hash_config_file(PROJECT_ROOT / "configs" / "gee.yaml"))"""
)

code(
    """# Phase test — zone Yaoundé
clusters_path = PROJECT_ROOT / "data/processed/dhs_prepared_with_buffers.parquet"
output_path = PROJECT_ROOT / "data/processed/features/cluster_features_gee_test.parquet"
output_path.parent.mkdir(parents=True, exist_ok=True)

features_df = extract_from_clusters_file(
    clusters_path=clusters_path,
    config=gee_config,
    mode="test",
)
features_df.to_parquet(output_path, index=False)
print(f"Extraction terminée : {len(features_df)} grappes")
features_df.describe().round(3)"""
)

code(
    """# QA : corrélations et aperçu
import pandas as pd
import geopandas as gpd
from src.data.merge_features import merge_dhs_with_features

gdf = gpd.read_parquet(clusters_path)
merged = merge_dhs_with_features(gdf, features_df)
cols = gee_config["feature_columns"]
print(merged[cols].corrwith(merged["wealth_index"]).sort_values().round(3))"""
)

md(
    """## Limites

- Couverture nuageuse Sentinel-2 variable selon les saisons
- OSM : couverture inégale en zone rurale
- WorldCover 2021 vs DHS 2018 : décalage temporel sur `built_density`
- Phase test uniquement — l'export national se fait via `scripts/extract_gee_features.py --mode national`

## Prochaines étapes

1. Valider QA sur la zone test
2. Extraction sur toutes les grappes (`--mode clusters`)
3. Basculer `features.fake: false` et ré-exécuter Notebook 02
4. Export raster national pour Notebook 03 (inférence)"""
)

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "cells": cells,
}

out = Path(__file__).resolve().parent.parent / "notebooks" / "03_gee_feature_extraction.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out}")