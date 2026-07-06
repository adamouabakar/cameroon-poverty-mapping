"""
Préparation des grappes DHS Cameroun 2018 réelles pour la modélisation.

Pipeline :
  1. Charger GPS (shapefile CMGE ou .dta) + ménages HR (.dta)
  2. Agréger wealth_index (hv271) au niveau grappe
  3. Coordonnées : fichier GE officiel (déjà jitterées DHS) ou simulation jitter
  4. Buffers 2 km (urbain) / 5 km (rural)
  5. Parquet + rapport QA
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from src.data.jitter import validate_buffer_covers_jitter
from src.data.load_dhs import load_dhs_clusters
from src.data.prepare_labels import create_cluster_buffers
from src.utils.helpers import get_project_root

DEFAULT_OUTPUT = "data/processed/dhs_clusters_real.parquet"
DEFAULT_QA_REPORT = "outputs/reports/dhs_real_qa.json"


def _normalize_region_name(series: pd.Series) -> pd.Series:
    """Uniformise les noms de région DHS (ex. EXTREME-NORD → Extrême-Nord)."""
    mapping = {
        "EXTREME-NORD": "Extrême-Nord",
        "NORD-OUEST": "Nord-Ouest",
        "SUD-OUEST": "Sud-Ouest",
        "ADAMAOUA": "Adamaoua",
        "CENTRE": "Centre",
        "EST": "Est",
        "LITTORAL": "Littoral",
        "NORD": "Nord",
        "OUEST": "Ouest",
        "SUD": "Sud",
        "DOUALA": "Douala",
        "YAOUNDE": "Yaoundé",
    }
    upper = series.astype(str).str.strip().str.upper()
    return upper.map(mapping).fillna(series.astype(str).str.strip())


def build_qa_report(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Rapport qualité pour les grappes DHS réelles."""
    cols = [
        "cluster_id", "latitude", "longitude", "urban_rural",
        "wealth_index", "region", "geometry",
    ]
    missing_rates = {
        col: float(gdf[col].isna().mean()) if col in gdf.columns else 1.0
        for col in cols
    }

    urban_counts = gdf["urban_rural"].value_counts().to_dict() if "urban_rural" in gdf.columns else {}
    region_counts = (
        gdf["region"].value_counts().to_dict() if "region" in gdf.columns else {}
    )

    wealth = gdf["wealth_index"] if "wealth_index" in gdf.columns else pd.Series(dtype=float)
    wealth_stats = {
        "count": int(wealth.notna().sum()),
        "mean": float(wealth.mean()) if wealth.notna().any() else None,
        "std": float(wealth.std()) if wealth.notna().sum() > 1 else None,
        "min": float(wealth.min()) if wealth.notna().any() else None,
        "p25": float(wealth.quantile(0.25)) if wealth.notna().any() else None,
        "median": float(wealth.median()) if wealth.notna().any() else None,
        "p75": float(wealth.quantile(0.75)) if wealth.notna().any() else None,
        "max": float(wealth.max()) if wealth.notna().any() else None,
    }

    displacement = None
    if "displacement_source" in gdf.columns:
        displacement = gdf["displacement_source"].iloc[0]

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_clusters": len(gdf),
        "crs": str(gdf.crs),
        "displacement_source": displacement,
        "urban_rural_counts": urban_counts,
        "region_counts": region_counts,
        "wealth_index_stats": wealth_stats,
        "missing_rates": missing_rates,
        "qa_passed": (
            len(gdf) > 0
            and missing_rates.get("wealth_index", 1.0) == 0.0
            and missing_rates.get("geometry", 1.0) == 0.0
        ),
    }


def prepare_real_dhs_clusters(
    dhs_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    qa_report_path: str | Path | None = None,
    random_state: int = 42,
    project_root: Path | None = None,
) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    """
    Construit le jeu de grappes DHS réelles avec buffers et rapport QA.

    Returns
    -------
    gdf : GeoDataFrame prêt pour extraction GEE / Notebook 02
    qa_report : dict rapport qualité
    """
    root = project_root or get_project_root()
    out_path = Path(output_path or root / DEFAULT_OUTPUT)
    report_path = Path(qa_report_path or root / DEFAULT_QA_REPORT)

    print("📥 Chargement des grappes DHS réelles...")
    gdf = load_dhs_clusters(
        dhs_dir=dhs_dir or root / "data/raw/dhs",
        use_fake=False,
        apply_jitter=None,
        random_state=random_state,
    )

    if "region" in gdf.columns:
        gdf["region"] = _normalize_region_name(gdf["region"])

    print(f"   → {len(gdf)} grappes chargées")

    print("🗺️  Création des buffers (2 km urbain / 5 km rural)...")
    gdf = create_cluster_buffers(gdf, urban_buffer_km=2.0, rural_buffer_km=5.0)

    if "jitter_distance_km" in gdf.columns and gdf["jitter_distance_km"].notna().any():
        validate_buffer_covers_jitter(gdf["buffer_km"], gdf["jitter_distance_km"])

    keep_cols = [
        "cluster_id", "latitude", "longitude", "urban_rural", "region",
        "wealth_index", "buffer_km", "geometry",
    ]
    optional = ["jitter_distance_km", "jitter_extended", "displacement_source"]
    keep_cols.extend(c for c in optional if c in gdf.columns)
    gdf = gdf[[c for c in keep_cols if c in gdf.columns]]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(out_path, index=False)
    print(f"💾 Parquet sauvegardé : {out_path}")

    qa_report = build_qa_report(gdf)
    qa_report["output_path"] = str(out_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(qa_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📋 Rapport QA : {report_path}")

    return gdf, qa_report