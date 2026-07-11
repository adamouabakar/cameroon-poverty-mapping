"""Validation externe : prédictions modèle vs statistiques officielles INS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from src.ins.regions import harmonize_region_name


def aggregate_predictions_by_region(
    clusters: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    pred_col: str = "y_oof_pred",
    cluster_col: str = "cluster_id",
    region_col: str = "region",
) -> pd.DataFrame:
    """Moyenne des prédictions OOF par région DHS."""
    merged = clusters[[cluster_col, region_col]].merge(
        predictions[[cluster_col, pred_col]],
        on=cluster_col,
        how="inner",
    )
    merged[region_col] = harmonize_region_name(merged[region_col])
    agg = (
        merged.groupby(region_col, as_index=False)
        .agg(
            n_clusters=(cluster_col, "count"),
            mean_predicted_wealth=(pred_col, "mean"),
            std_predicted_wealth=(pred_col, "std"),
            median_predicted_wealth=(pred_col, "median"),
        )
    )
    return agg


def build_validation_table(
    regional_preds: pd.DataFrame,
    ins_df: pd.DataFrame,
    *,
    region_col: str = "region",
) -> pd.DataFrame:
    """Tableau comparatif région par région."""
    ins = ins_df.copy()
    ins["region_dhs"] = harmonize_region_name(ins["region_dhs"])
    table = regional_preds.merge(
        ins,
        left_on=region_col,
        right_on="region_dhs",
        how="inner",
    )
    table["wealth_rank"] = table["mean_predicted_wealth"].rank(ascending=False, method="average")
    table["poverty_rank"] = table["poverty_rate_pct"].rank(ascending=False, method="average")
    table["rank_gap"] = (table["wealth_rank"] - table["poverty_rank"]).abs()
    table["abs_error_poverty_vs_wealth_pct"] = (
        _scale_wealth_to_poverty_proxy(table["mean_predicted_wealth"])
        - table["poverty_rate_pct"]
    ).abs()
    return table.sort_values("poverty_rate_pct", ascending=False)


def _scale_wealth_to_poverty_proxy(wealth: pd.Series) -> pd.Series:
    """
    Met l'échelle wealth DHS sur 0–100 pour comparer visuellement à la pauvreté %.
    Min-max sur l'échantillon régional (indicatif uniquement).
    """
    w = wealth.astype(float)
    w_min, w_max = w.min(), w.max()
    if w_max <= w_min:
        return pd.Series(50.0, index=w.index)
    # Wealth élevé → faible pauvreté proxy
    wealth_norm = (w - w_min) / (w_max - w_min)
    return (1.0 - wealth_norm) * 100.0


def compute_validation_metrics(table: pd.DataFrame) -> dict[str, Any]:
    """Métriques de concordance modèle ↔ INS."""
    x = table["mean_predicted_wealth"].astype(float)
    y_poverty = table["poverty_rate_pct"].astype(float)
    y_literacy = table["literacy_rate_15plus_pct"].astype(float)
    y_electricity = table["electricity_access_pct"].astype(float)

    spearman_poverty, p_poverty = stats.spearmanr(x, y_poverty)
    pearson_poverty, _ = stats.pearsonr(x, y_poverty)

    spearman_literacy, _ = stats.spearmanr(x, y_literacy)
    spearman_electricity, _ = stats.spearmanr(x, y_electricity)

    poverty_proxy = _scale_wealth_to_poverty_proxy(x)
    mae = float(np.mean(np.abs(poverty_proxy - y_poverty)))
    rmse = float(np.sqrt(np.mean((poverty_proxy - y_poverty) ** 2)))
    bias = float(np.mean(poverty_proxy - y_poverty))

    rank_gap_mean = float(table["rank_gap"].mean())
    rank_gap_max = float(table["rank_gap"].max())

    return {
        "n_regions": int(len(table)),
        "spearman_wealth_vs_poverty": float(spearman_poverty),
        "spearman_p_value": float(p_poverty),
        "pearson_wealth_vs_poverty": float(pearson_poverty),
        "spearman_wealth_vs_literacy": float(spearman_literacy),
        "spearman_wealth_vs_electricity": float(spearman_electricity),
        "mae_poverty_proxy_pct": mae,
        "rmse_poverty_proxy_pct": rmse,
        "bias_poverty_proxy_pct": bias,
        "mean_rank_gap": rank_gap_mean,
        "max_rank_gap": rank_gap_max,
        "interpretation": {
            "expected_spearman_poverty": "Négatif si le modèle classe correctement les régions pauvres vs riches.",
            "proxy_warning": "wealth_index DHS (actifs) ≠ pauvreté monétaire ECAM — comparer surtout les rangs.",
            "temporal_gap": "DHS 2018 vs ECAM 2014 — écart temporel ~4 ans.",
        },
    }


def plot_validation_scatter(
    table: pd.DataFrame,
    output_path: Path,
    *,
    region_col: str = "region",
) -> Path:
    """Scatter wealth prédit vs pauvreté INS par région."""
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        table["poverty_rate_pct"],
        table["mean_predicted_wealth"],
        s=table["n_clusters"] * 3,
        alpha=0.75,
        edgecolors="k",
        linewidths=0.5,
    )
    for _, row in table.iterrows():
        ax.annotate(
            row[region_col],
            (row["poverty_rate_pct"], row["mean_predicted_wealth"]),
            fontsize=7,
            alpha=0.85,
        )
    ax.set_xlabel("Pauvreté monétaire INS/ECAM 4 (%)")
    ax.set_ylabel("Wealth index prédit (moyenne OOF grappes)")
    ax.set_title("Validation externe — modèle vs INS par région")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path