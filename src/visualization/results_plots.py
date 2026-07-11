"""Graphiques de diagnostic du modèle (OOF, importance, résidus, comparaisons)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

CHIRPS_COLS = {"precip_annual_mm", "precip_wet_season_mm", "precip_cv"}
GHSL_COL = "ghsl_built_fraction"
INS_PREFIX = "ins_"


def _feature_color(feature: str) -> str:
    if feature.startswith(INS_PREFIX):
        return "#c0392b"
    if feature in CHIRPS_COLS:
        return "#27ae60"
    if feature == GHSL_COL:
        return "#2980b9"
    return "#7f8c8d"


def plot_oof_scatter(
    oof_df: pd.DataFrame,
    metrics: dict,
    out_path: Path,
    *,
    y_col: str = "y_true",
    pred_col: str = "y_oof_pred",
) -> None:
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(oof_df[y_col], oof_df[pred_col], alpha=0.45, s=35, c="#2c3e50", edgecolors="none")
    lims = [
        min(oof_df[y_col].min(), oof_df[pred_col].min()),
        max(oof_df[y_col].max(), oof_df[pred_col].max()),
    ]
    ax.plot(lims, lims, "r--", lw=1.2, label="y = x")
    z = np.polyfit(oof_df[y_col], oof_df[pred_col], 1)
    p = np.poly1d(z)
    xs = np.linspace(lims[0], lims[1], 100)
    ax.plot(xs, p(xs), color="#e67e22", lw=1.2, label="Régression OOF")
    ax.set_xlabel("Wealth index observé (hv271)")
    ax.set_ylabel("Prédiction OOF")
    ax.set_title(
        f"Prédictions OOF vs réel — R²={metrics.get('r2', 0):.3f}, "
        f"Spearman={metrics.get('spearman', 0):.3f}"
    )
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_residuals(oof_df: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.histplot(oof_df["residual"], kde=True, ax=axes[0], color="#8e44ad")
    axes[0].axvline(0, color="red", ls="--", lw=1)
    axes[0].set_title("Distribution des résidus OOF")
    axes[0].set_xlabel("Résidu (observé − prédit)")

    axes[1].scatter(oof_df["y_oof_pred"], oof_df["residual"], alpha=0.4, s=30, c="#16a085")
    axes[1].axhline(0, color="red", ls="--", lw=1)
    axes[1].set_xlabel("Prédiction OOF")
    axes[1].set_ylabel("Résidu")
    axes[1].set_title("Résidus vs prédictions")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_feature_importance(
    importance: dict,
    out_path: Path,
    *,
    top_n: int = 15,
    title: str = "Feature importance (gain LightGBM)",
) -> None:
    ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
    features = [f for f, _ in ranked][::-1]
    gains = [g for _, g in ranked][::-1]
    colors = [_feature_color(f) for f in features]

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(features, gains, color=colors)
    ax.set_xlabel("Gain LightGBM")
    ax.set_title(title)
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(color="#27ae60", label="CHIRPS"),
        Patch(color="#2980b9", label="GHSL"),
        Patch(color="#7f8c8d", label="GEE / OSM"),
    ]
    if any(f.startswith(INS_PREFIX) for f in features):
        legend_handles.append(Patch(color="#c0392b", label="INS (ECAM 4)"))
    ax.legend(handles=legend_handles, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_metrics_comparison(
    real_results_path: Path,
    out_path: Path,
) -> None:
    """Compare fake v2/v3 vs real v2/v3 (métriques OOF)."""
    data = json.loads(real_results_path.read_text(encoding="utf-8"))
    comp = data["comparison"]

    rows = [
        ("Fake v2", comp.get("real_vs_fake_v3", {}).get("fake_metrics")),  # placeholder
        ("Fake v3", comp["real_vs_fake_v3"]["fake_metrics"]),
        ("Réel v2", comp["v2_vs_v3_real"]["v2_metrics"]),
        ("Réel v3", comp["real_vs_fake_v3"]["real_metrics"]),
    ]
    # Fix fake v2 from v2_vs_v3 fake file if needed — use only available
    labels, r2, spearman = [], [], []
    for label, m in rows:
        if m is None:
            continue
        labels.append(label)
        r2.append(m.get("r2", 0))
        spearman.append(m.get("spearman", 0))

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, r2, width, label="R² OOF", color="#3498db")
    ax.bar(x + width / 2, spearman, width, label="Spearman OOF", color="#e74c3c")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_title("Comparaison des performances — fake vs réel, v2 vs v3")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_v3_v4_metrics(
    v4_results_path: Path,
    out_path: Path,
) -> None:
    """Barres côte à côte v3 vs v4 (R², Spearman)."""
    data = json.loads(v4_results_path.read_text(encoding="utf-8"))
    comp = data["comparison_v3_vs_v4"]["metrics"]
    v3 = comp["v3"]
    v4 = comp["v4"]

    metrics = ["r2", "spearman"]
    labels = ["R² OOF", "Spearman OOF"]
    v3_vals = [v3[k] for k in metrics]
    v4_vals = [v4[k] for k in metrics]

    x = np.arange(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, v3_vals, width, label="v3 (GEE)", color="#3498db")
    ax.bar(x + width / 2, v4_vals, width, label="v4 (GEE + INS)", color="#e74c3c")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.0)
    ax.set_title("Comparaison OOF — modèle v3 vs v4")
    delta = comp["delta_v4_minus_v3"]
    ax.text(
        0.02, 0.98,
        f"Δ R² = {delta['r2']:+.4f}  |  Δ Spearman = {delta['spearman']:+.4f}",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)