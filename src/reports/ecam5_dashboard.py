"""Comparaison régionale ECAM 5 vs prédictions modèle."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ins.load_ecam5 import load_ecam5_contextual_data
from src.ins.regions import harmonize_region_name
from src.reports.region_stats import load_cluster_frame


def build_ecam5_model_comparison(project_root: Path) -> pd.DataFrame:
    """Tableau région : pauvreté ECAM5, wealth prédit moyen, écart de rang."""
    clusters = load_cluster_frame(project_root)
    ecam5 = load_ecam5_contextual_data(
        output_path=None,
        project_root=project_root,
    )

    regional = (
        clusters.groupby("region", as_index=False)
        .agg(
            n_clusters=("cluster_id", "count"),
            mean_predicted_wealth=("predicted_wealth", "mean"),
            mean_uncertainty=("uncertainty_width", "mean"),
        )
    )
    regional["region"] = harmonize_region_name(regional["region"])

    ins = ecam5.copy()
    ins["region"] = harmonize_region_name(ins["region_dhs"])
    ins = ins.drop_duplicates(subset=["region"], keep="first")

    table = regional.merge(
        ins[["region", "poverty_rate_pct", "literacy_rate_15plus_pct", "source_year"]],
        on="region",
        how="inner",
    )
    table["wealth_rank"] = table["mean_predicted_wealth"].rank(ascending=False, method="average")
    table["poverty_rank"] = table["poverty_rate_pct"].rank(ascending=False, method="average")
    table["rank_gap"] = (table["wealth_rank"] - table["poverty_rank"]).abs()
    table = table.sort_values("poverty_rate_pct", ascending=False)

    return table.round(
        {
            "mean_predicted_wealth": 1,
            "mean_uncertainty": 1,
            "poverty_rate_pct": 1,
            "literacy_rate_15plus_pct": 1,
            "rank_gap": 1,
        }
    )