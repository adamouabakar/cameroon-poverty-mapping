"""Modèle spatio-temporel exploratoire — panel grappes 2014/2018/2022."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

from src.ins.load_ins import load_ins_contextual_data
from src.ins.load_ecam5 import load_ecam5_contextual_data
from src.ins.regions import harmonize_region_name

PANEL_YEARS = (2014, 2018, 2022)
ANCHOR_YEAR = 2018


def _region_poverty_lookup(df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    for _, row in df.iterrows():
        key = harmonize_region_name(pd.Series([row["region_dhs"]])).iloc[0]
        out[key] = float(row["poverty_rate_pct"])
    return out


def _wealth_adjustment_from_poverty_delta(delta_poverty_pct: float, *, scale: float = 800.0) -> float:
    """Pauvreté en hausse → wealth proxy en baisse (échelle indicative)."""
    return -delta_poverty_pct * scale


def build_temporal_panel(
    clusters: gpd.GeoDataFrame,
    oof: pd.DataFrame,
    *,
    ecam4_path: str | Path = "data/reference/ins/ecam4_regional_indicators.csv",
    ecam5_path: str | Path = "data/reference/ins/ecam5_regional_indicators.csv",
    project_root: Path | None = None,
) -> pd.DataFrame:
    """
    Construit un panel long : une ligne par (cluster_id, year).

    2018 ancré sur y_oof_pred ; 2014/2022 ajustés via deltas pauvreté INS régionaux.
    """
    root = project_root or Path.cwd()
    ecam4 = load_ins_contextual_data(raw_path=ecam4_path, output_path=None, project_root=root)
    ecam5 = load_ecam5_contextual_data(raw_path=ecam5_path, output_path=None, project_root=root)

    p2014 = _region_poverty_lookup(ecam4)
    p2022 = _region_poverty_lookup(ecam5)

    base = clusters.merge(
        oof[["cluster_id", "y_oof_pred", "y_true"]],
        on="cluster_id",
        how="inner",
    )
    base["region"] = harmonize_region_name(base["region"])

    rows: list[dict[str, Any]] = []
    for _, row in base.iterrows():
        region = str(row["region"])
        anchor = float(row["y_oof_pred"])
        p18 = p2014.get(region, np.nan)
        p22 = p2022.get(region, np.nan)
        if not np.isfinite(p18):
            p18 = float(np.nanmean(list(p2014.values())))
        if not np.isfinite(p22):
            p22 = float(np.nanmean(list(p2022.values())))

        # 2018 : midpoint poverty proxy between ECAM4 and ECAM5
        p18_mid = (p18 + p22) / 2.0

        year_poverty = {
            2014: p18,
            2018: p18_mid,
            2022: p22,
        }
        for year in PANEL_YEARS:
            delta = year_poverty[year] - p18_mid
            adj = _wealth_adjustment_from_poverty_delta(delta)
            rows.append(
                {
                    "cluster_id": int(row["cluster_id"]),
                    "year": year,
                    "region": region,
                    "urban_rural": str(row.get("urban_rural", "")),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "predicted_wealth": anchor + adj,
                    "anchor_2018": anchor,
                    "dhs_wealth_2018": float(row["y_true"]),
                    "regional_poverty_pct": year_poverty[year],
                    "poverty_delta_vs_2018": delta,
                    "wealth_adjustment": adj,
                    "source": "ins_regional_trend_proxy",
                }
            )

    return pd.DataFrame(rows)


def compute_temporal_metrics(panel: pd.DataFrame) -> dict[str, Any]:
    """Métriques de cohérence temporelle régionale."""
    regional = (
        panel.groupby(["year", "region"], as_index=False)
        .agg(
            mean_wealth=("predicted_wealth", "mean"),
            mean_poverty=("regional_poverty_pct", "mean"),
            n_clusters=("cluster_id", "count"),
        )
    )

    spearman_by_year: dict[int, float] = {}
    for year, grp in regional.groupby("year"):
        if len(grp) < 3:
            continue
        rho, _ = stats.spearmanr(grp["mean_wealth"], grp["mean_poverty"])
        spearman_by_year[int(year)] = float(rho)

    y2018 = panel[panel["year"] == 2018]
    y2022 = panel[panel["year"] == 2022]
    merged = y2018.merge(
        y2022,
        on="cluster_id",
        suffixes=("_2018", "_2022"),
    )
    cluster_trend_rho, _ = stats.spearmanr(
        merged["predicted_wealth_2018"],
        merged["predicted_wealth_2022"],
    )

    return {
        "n_clusters": int(panel["cluster_id"].nunique()),
        "years": sorted(panel["year"].unique().tolist()),
        "n_panel_rows": int(len(panel)),
        "spearman_wealth_vs_poverty_by_year": spearman_by_year,
        "spearman_cluster_2018_vs_2022": float(cluster_trend_rho),
        "mean_wealth_shift_2018_to_2022": float(
            (y2022["predicted_wealth"].mean() - y2018["predicted_wealth"].mean())
        ),
        "interpretation": (
            "Panel exploratoire : ajustements régionaux INS ECAM4/5, "
            "pas de micro-données temporelles GEE."
        ),
    }


def panel_to_geojson_records(panel: pd.DataFrame) -> dict[str, list[dict]]:
    """Format léger pour site/temporal.html — par année."""
    out: dict[str, list[dict]] = {}
    for year in sorted(panel["year"].unique()):
        sub = panel[panel["year"] == year]
        out[str(int(year))] = [
            {
                "id": int(r.cluster_id),
                "lat": round(float(r.latitude), 5),
                "lon": round(float(r.longitude), 5),
                "w": round(float(r.predicted_wealth), 1),
                "r": str(r.region),
            }
            for r in sub.itertuples(index=False)
        ]
    return out