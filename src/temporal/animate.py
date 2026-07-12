"""Animation temporelle — GIF régional + export JSON web."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, PillowWriter

from src.temporal.panel_model import panel_to_geojson_records


def plot_regional_temporal_gif(panel: pd.DataFrame, output_path: Path) -> Path:
    """GIF : barres pauvreté régionale par année."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    regional = (
        panel.groupby(["year", "region"], as_index=False)
        .agg(mean_wealth=("predicted_wealth", "mean"))
        .sort_values(["year", "mean_wealth"])
    )
    years = sorted(regional["year"].unique())
    regions = sorted(regional["region"].unique())

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.RdYlGn(np.linspace(0.15, 0.85, len(regions)))

    def _frame(i: int):
        ax.clear()
        year = years[i]
        sub = regional[regional["year"] == year].set_index("region").reindex(regions)
        vals = sub["mean_wealth"].fillna(0).to_numpy()
        ax.barh(regions, vals, color=colors)
        ax.set_xlabel("Wealth index prédit (moyenne régionale)")
        ax.set_title(f"Évolution exploratoire — {year}")
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()

    anim = FuncAnimation(fig, _frame, frames=len(years), interval=1200, repeat=True)
    anim.save(output_path, writer=PillowWriter(fps=1))
    plt.close(fig)
    return output_path


def export_temporal_web_assets(panel: pd.DataFrame, site_assets: Path) -> Path:
    """Écrit site/assets/temporal_panel.json pour temporal.html."""
    site_assets = Path(site_assets)
    site_assets.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "years": sorted(int(y) for y in panel["year"].unique()),
        "ethics": "exploratory_ins_trend_proxy_no_official_stats",
        "clusters_by_year": panel_to_geojson_records(panel),
        "regional_means": (
            panel.groupby(["year", "region"], as_index=False)
            .agg(mean_wealth=("predicted_wealth", "mean"))
            .to_dict(orient="records")
        ),
    }
    out = site_assets / "temporal_panel.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out