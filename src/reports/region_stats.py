"""Statistiques administratives DHS par région."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.ins.regions import harmonize_region_name

DHS_REGIONS = [
    "Tout le Cameroun",
    "Extrême-Nord",
    "Nord",
    "Adamaoua",
    "Est",
    "Centre",
    "Littoral",
    "Ouest",
    "Sud",
    "Sud-Ouest",
    "Nord-Ouest",
    "Douala",
    "Yaoundé",
]

REGION_BOUNDS: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "Extrême-Nord": ((10.0, 13.0), (12.5, 15.5)),
    "Nord": ((8.5, 13.0), (10.5, 15.0)),
    "Adamaoua": ((6.5, 12.0), (8.5, 14.5)),
    "Est": ((2.5, 13.5), (5.5, 16.0)),
    "Centre": ((3.5, 11.0), (5.5, 12.5)),
    "Littoral": ((3.5, 9.5), (5.0, 10.5)),
    "Ouest": ((5.0, 9.5), (6.5, 11.0)),
    "Sud": ((1.5, 9.5), (3.5, 11.5)),
    "Sud-Ouest": ((4.0, 8.5), (6.0, 10.0)),
    "Nord-Ouest": ((5.5, 9.5), (7.0, 11.0)),
    "Douala": ((4.0, 9.5), (4.3, 9.9)),
    "Yaoundé": ((3.7, 11.3), (4.0, 11.7)),
}


def load_cluster_frame(project_root: Path) -> pd.DataFrame:
    """Grappes DHS + prédictions OOF + incertitude."""
    clusters = gpd.read_parquet(project_root / "data/processed/dhs_clusters_real.parquet")
    oof = pd.read_parquet(project_root / "data/processed/training/oof_predictions.parquet")
    oof_cols = [
        c
        for c in ["cluster_id", "y_oof_pred", "y_true", "lower_90", "upper_90", "residual"]
        if c in oof.columns
    ]
    merged = clusters.merge(oof[oof_cols], on="cluster_id", how="inner")
    merged["region"] = harmonize_region_name(merged["region"])
    merged["uncertainty_width"] = (merged["upper_90"] - merged["lower_90"]).abs()
    merged["predicted_wealth"] = merged["y_oof_pred"]
    return merged


def compute_regional_summary(df: pd.DataFrame, *, region: str | None = None) -> pd.DataFrame:
    """Agrège métriques par région DHS."""
    sub = df if not region or region == "Tout le Cameroun" else df[df["region"] == region]
    if sub.empty:
        return pd.DataFrame()

    if region and region != "Tout le Cameroun":
        rows = [_agg_row(sub, region)]
        return pd.DataFrame(rows)

    rows = []
    for r in sorted(sub["region"].unique()):
        g = sub[sub["region"] == r]
        rows.append(_agg_row(g, r))
    national = _agg_row(sub, "Tout le Cameroun")
    return pd.DataFrame([national] + rows)


def _agg_row(g: pd.DataFrame, label: str) -> dict:
    urban = g[g["urban_rural"].astype(str).str.lower() == "urban"]
    rural = g[g["urban_rural"].astype(str).str.lower() == "rural"]
    return {
        "region": label,
        "n_clusters": int(len(g)),
        "n_urban": int(len(urban)),
        "n_rural": int(len(rural)),
        "wealth_mean": round(float(g["predicted_wealth"].mean()), 1),
        "wealth_median": round(float(g["predicted_wealth"].median()), 1),
        "wealth_std": round(float(g["predicted_wealth"].std()), 1),
        "dhs_wealth_mean": round(float(g["wealth_index"].mean()), 1),
        "uncertainty_mean": round(float(g["uncertainty_width"].mean()), 1),
        "residual_mean": round(float((g["predicted_wealth"] - g["wealth_index"]).mean()), 1),
    }


def filter_clusters_by_region(df: pd.DataFrame, region: str) -> pd.DataFrame:
    if region == "Tout le Cameroun":
        return df
    return df[df["region"] == region].copy()