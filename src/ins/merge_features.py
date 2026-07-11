"""Fusion des indicateurs INS contextuels avec grappes / features DHS."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ins.regions import INS_FEATURE_COLUMNS_V4, harmonize_region_name


def merge_ins_context_to_clusters(
    clusters: pd.DataFrame,
    ins_df: pd.DataFrame,
    *,
    region_col: str = "region",
) -> pd.DataFrame:
    """Joint les indicateurs INS (région) aux grappes DHS."""
    if region_col not in clusters.columns:
        raise KeyError(f"Colonne région absente : {region_col}")

    ins = ins_df.copy()
    ins["region_dhs"] = harmonize_region_name(ins["region_dhs"])

    rename = {
        "poverty_rate_pct": "ins_poverty_rate_pct",
        "literacy_rate_15plus_pct": "ins_literacy_rate_15plus_pct",
        "electricity_access_pct": "ins_electricity_access_pct",
        "primary_enrollment_pct": "ins_primary_enrollment_pct",
    }
    ins = ins.rename(columns=rename)
    keep = ["region_dhs", *INS_FEATURE_COLUMNS_V4, "source_survey", "source_year"]
    ins = ins[[c for c in keep if c in ins.columns]]

    out = clusters.copy()
    out["_region_join"] = harmonize_region_name(out[region_col])
    merged = out.merge(
        ins,
        left_on="_region_join",
        right_on="region_dhs",
        how="left",
        validate="m:1",
    )
    merged = merged.drop(columns=["_region_join", "region_dhs"], errors="ignore")

    missing = merged[INS_FEATURE_COLUMNS_V4].isna().any(axis=1).sum()
    if missing:
        raise ValueError(f"{missing} grappes sans correspondance INS après fusion.")

    return merged


def merge_ins_to_feature_parquet(
    features_path: Path,
    ins_df: pd.DataFrame,
    clusters_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    """
    Produit un parquet features v4 = features GEE v3 + colonnes INS régionales.
    """
    import geopandas as gpd

    features = pd.read_parquet(features_path)
    clusters = gpd.read_parquet(clusters_path)
    if "region" not in clusters.columns:
        raise KeyError("Grappes sans colonne region")

    region_map = clusters[["cluster_id", "region"]].drop_duplicates("cluster_id")
    merged = features.merge(region_map, on="cluster_id", how="left")
    merged = merge_ins_context_to_clusters(merged, ins_df, region_col="region")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(output_path, index=False)
    return merged