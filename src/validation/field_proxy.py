"""Proxy field validation using public DHS cluster ground truth."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.partner_web.field_validation import (
    SiteRow,
    enrich_with_rasters,
    sample_raster_at,
    value_to_bin,
    _tercile_edges,
)
from src.partner_web.render import load_master_wealth


BIN_ORDER = {"bas": 0, "moyen": 1, "haut": 2}


@dataclass
class ProxySiteMetrics:
    cluster_id: int
    region: str
    urban_rural: str
    lat: float
    lon: float
    dhs_wealth: float
    oof_pred: float
    map_wealth: float | None
    map_uncertainty: float | None
    dhs_bin: str
    oof_bin: str
    map_bin: str | None
    local_assessment: str
    concordance: str
    residual_oof: float
    residual_raster: float | None


def select_stratified_clusters(
    clusters: pd.DataFrame,
    *,
    min_per_region: int = 1,
    seed: int = 42,
) -> pd.DataFrame:
    """Pick DHS clusters stratified by region (and urban/rural when possible)."""
    rng = np.random.default_rng(seed)
    required = {"cluster_id", "latitude", "longitude", "region", "wealth_index", "urban_rural"}
    missing = required - set(clusters.columns)
    if missing:
        raise ValueError(f"clusters missing columns: {sorted(missing)}")

    picks: list[pd.DataFrame] = []
    for region, grp in clusters.groupby("region", sort=True):
        urban = grp[grp["urban_rural"].astype(str).str.lower() == "urban"]
        rural = grp[grp["urban_rural"].astype(str).str.lower() == "rural"]
        chosen_idx: list[int] = []

        if len(urban) >= 1 and len(rural) >= 1 and min_per_region >= 2:
            chosen_idx.extend(
                [
                    int(urban.sample(1, random_state=int(rng.integers(0, 1_000_000))).index[0]),
                    int(rural.sample(1, random_state=int(rng.integers(0, 1_000_000))).index[0]),
                ]
            )
        else:
            n = min(min_per_region, len(grp))
            chosen_idx.extend(
                grp.sample(n, random_state=int(rng.integers(0, 1_000_000))).index.tolist()
            )
        picks.append(grp.loc[chosen_idx])

    out = pd.concat(picks, ignore_index=True)
    return out.sort_values(["region", "cluster_id"]).reset_index(drop=True)


def wealth_series_to_bins(values: pd.Series) -> pd.Series:
    lo, hi = _tercile_edges(values.astype(float).to_numpy())
    return values.astype(float).apply(lambda v: value_to_bin(float(v), lo, hi))


def local_assessment_from_bins(dhs_bin: str, map_bin: str) -> str:
    d = BIN_ORDER.get(dhs_bin, 1)
    m = BIN_ORDER.get(map_bin, 1)
    if d < m:
        return "plus pauvre"
    if d > m:
        return "plus aisé"
    return "similaire"


def concordance_from_assessment(local: str, map_bin: str) -> str:
    if local == "similaire":
        return "match"
    if local == "plus pauvre":
        if map_bin == "bas":
            return "match"
        if map_bin == "moyen":
            return "partial"
        return "mismatch"
    if local in ("plus aisé", "plus aise"):
        if map_bin == "haut":
            return "match"
        if map_bin == "moyen":
            return "partial"
        return "mismatch"
    return "unknown"


def build_proxy_sites(
    clusters: pd.DataFrame,
    oof: pd.DataFrame,
    *,
    wealth_path: Path,
    uncertainty_path: Path,
    min_per_region: int = 1,
    seed: int = 42,
) -> tuple[list[ProxySiteMetrics], dict[str, float]]:
    """Build proxy site metrics: DHS ground truth vs OOF vs raster."""
    selected = select_stratified_clusters(clusters, min_per_region=min_per_region, seed=seed)
    merged = selected.merge(
        oof[["cluster_id", "y_oof_pred", "y_true"]],
        on="cluster_id",
        how="inner",
    )
    if merged.empty:
        raise ValueError("no clusters matched OOF predictions")

    dhs_bins = wealth_series_to_bins(merged["wealth_index"])
    oof_bins = wealth_series_to_bins(merged["y_oof_pred"])

    coords = list(zip(merged["longitude"].astype(float), merged["latitude"].astype(float)))
    map_w = sample_raster_at(wealth_path, coords)
    map_u = sample_raster_at(uncertainty_path, coords)

    wealth_arr, transform, crs = load_master_wealth(wealth_path, max_edge=512)
    w_lo, w_hi = _tercile_edges(np.asarray(wealth_arr, dtype=float))

    sites: list[ProxySiteMetrics] = []
    for idx, (_, row) in enumerate(merged.iterrows()):
        mw = map_w[idx]
        mu = map_u[idx]
        dhs_bin = str(dhs_bins.iloc[idx])
        oof_bin = str(oof_bins.iloc[idx])
        map_bin = value_to_bin(mw, w_lo, w_hi) if mw is not None else None
        local = local_assessment_from_bins(dhs_bin, map_bin or oof_bin)
        conc = concordance_from_assessment(local, map_bin or oof_bin)
        sites.append(
            ProxySiteMetrics(
                cluster_id=int(row["cluster_id"]),
                region=str(row["region"]),
                urban_rural=str(row["urban_rural"]),
                lat=float(row["latitude"]),
                lon=float(row["longitude"]),
                dhs_wealth=float(row["wealth_index"]),
                oof_pred=float(row["y_oof_pred"]),
                map_wealth=mw,
                map_uncertainty=mu,
                dhs_bin=dhs_bin,
                oof_bin=oof_bin,
                map_bin=map_bin,
                local_assessment=local,
                concordance=conc,
                residual_oof=float(row["y_oof_pred"] - row["wealth_index"]),
                residual_raster=(mw - float(row["wealth_index"])) if mw is not None else None,
            )
        )

    dhs = merged["wealth_index"].astype(float)
    oof_pred = merged["y_oof_pred"].astype(float)
    map_vals = np.array([s.map_wealth for s in sites if s.map_wealth is not None], dtype=float)
    dhs_for_map = np.array(
        [s.dhs_wealth for s in sites if s.map_wealth is not None], dtype=float
    )

    metrics: dict[str, float] = {
        "n_sites": float(len(sites)),
        "n_regions": float(merged["region"].nunique()),
        "spearman_oof_vs_dhs": float(stats.spearmanr(oof_pred, dhs).statistic),
        "pearson_oof_vs_dhs": float(stats.pearsonr(oof_pred, dhs).statistic),
        "mae_oof": float(np.mean(np.abs(oof_pred - dhs))),
        "rmse_oof": float(np.sqrt(np.mean((oof_pred - dhs) ** 2))),
    }
    if map_vals.size:
        metrics.update(
            {
                "spearman_raster_vs_dhs": float(stats.spearmanr(map_vals, dhs_for_map).statistic),
                "pearson_raster_vs_dhs": float(stats.pearsonr(map_vals, dhs_for_map).statistic),
                "mae_raster": float(np.mean(np.abs(map_vals - dhs_for_map))),
                "rmse_raster": float(np.sqrt(np.mean((map_vals - dhs_for_map) ** 2))),
                "spearman_raster_vs_oof": float(
                    stats.spearmanr(
                        map_vals,
                        np.array([s.oof_pred for s in sites if s.map_wealth is not None]),
                    ).statistic
                ),
            }
        )

    counts = {"match": 0, "partial": 0, "mismatch": 0, "unknown": 0}
    for s in sites:
        counts[s.concordance] = counts.get(s.concordance, 0) + 1
    metrics["concordance_match_pct"] = 100.0 * counts["match"] / max(len(sites), 1)
    metrics["concordance_partial_pct"] = 100.0 * counts["partial"] / max(len(sites), 1)
    metrics["concordance_mismatch_pct"] = 100.0 * counts["mismatch"] / max(len(sites), 1)

    return sites, metrics


def proxy_sites_to_csv_rows(sites: list[ProxySiteMetrics]) -> list[SiteRow]:
    rows: list[SiteRow] = []
    for s in sites:
        ubin = "moyen"
        if s.map_uncertainty is not None:
            ubin = "moyen"
        rows.append(
            SiteRow(
                site_id=f"proxy_c{s.cluster_id}",
                region=s.region,
                lat=s.lat,
                lon=s.lon,
                predicted_wealth_bin=s.oof_bin,
                uncertainty_bin=ubin,
                local_assessment=s.local_assessment,
                notes=(
                    f"Proxy DHS wealth={s.dhs_wealth:.0f}; "
                    f"urban_rural={s.urban_rural}; map_bin={s.map_bin or 'na'}"
                ),
                observer="post_v1_proxy_dhs2018",
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                map_wealth=s.map_wealth,
                map_uncertainty=s.map_uncertainty,
                map_wealth_bin=s.map_bin,
                concordance=s.concordance,
            )
        )
    return rows


def write_proxy_csv(sites: list[ProxySiteMetrics], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "site_id",
        "region",
        "lat",
        "lon",
        "predicted_wealth_bin",
        "uncertainty_bin",
        "local_assessment",
        "notes",
        "observer",
        "date",
        "dhs_wealth",
        "oof_pred",
        "map_wealth",
        "dhs_bin",
        "map_bin",
        "concordance",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for s in sites:
            w.writerow(
                {
                    "site_id": f"proxy_c{s.cluster_id}",
                    "region": s.region,
                    "lat": f"{s.lat:.6f}",
                    "lon": f"{s.lon:.6f}",
                    "predicted_wealth_bin": s.oof_bin,
                    "uncertainty_bin": "moyen",
                    "local_assessment": s.local_assessment,
                    "notes": (
                        f"DHS proxy; urban_rural={s.urban_rural}; "
                        f"dhs_bin={s.dhs_bin}; map_bin={s.map_bin or 'na'}"
                    ),
                    "observer": "post_v1_proxy_dhs2018",
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "dhs_wealth": f"{s.dhs_wealth:.4f}",
                    "oof_pred": f"{s.oof_pred:.4f}",
                    "map_wealth": "" if s.map_wealth is None else f"{s.map_wealth:.4f}",
                    "dhs_bin": s.dhs_bin,
                    "map_bin": s.map_bin or "",
                    "concordance": s.concordance,
                }
            )


def plot_proxy_scatter(sites: list[ProxySiteMetrics], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dhs = np.array([s.dhs_wealth for s in sites], dtype=float)
    oof = np.array([s.oof_pred for s in sites], dtype=float)
    raster = np.array([s.map_wealth if s.map_wealth is not None else np.nan for s in sites])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].scatter(dhs, oof, alpha=0.7, edgecolors="k", linewidths=0.3, s=40)
    axes[0].plot([dhs.min(), dhs.max()], [dhs.min(), dhs.max()], "r--", alpha=0.5, lw=1)
    axes[0].set_xlabel("DHS wealth_index (terrain proxy)")
    axes[0].set_ylabel("OOF prédiction modèle")
    axes[0].set_title("Grappes DHS — OOF vs référence")
    axes[0].grid(True, alpha=0.3)

    mask = np.isfinite(raster)
    if mask.any():
        axes[1].scatter(dhs[mask], raster[mask], alpha=0.7, edgecolors="k", linewidths=0.3, s=40)
        lo, hi = dhs[mask].min(), dhs[mask].max()
        axes[1].plot([lo, hi], [lo, hi], "r--", alpha=0.5, lw=1)
    axes[1].set_xlabel("DHS wealth_index (terrain proxy)")
    axes[1].set_ylabel("Raster national échantillonné")
    axes[1].set_title("Grappes DHS — Raster vs référence")
    axes[1].grid(True, alpha=0.3)

    fig.suptitle("Validation terrain proxy — données publiques DHS 2018", fontsize=11)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def write_proxy_report(
    sites: list[ProxySiteMetrics],
    metrics: dict[str, float],
    *,
    out_json: Path,
    out_md: Path,
    ins_metrics: dict[str, Any] | None = None,
) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    counts = {"match": 0, "partial": 0, "mismatch": 0, "unknown": 0}
    for s in sites:
        counts[s.concordance] = counts.get(s.concordance, 0) + 1

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "action": "post_v1_action1_field_proxy",
        "methodology": {
            "ground_truth_proxy": "DHS 2018 cluster wealth_index (public microdata aggregates)",
            "sites": "Stratified DHS cluster centroids by region (+ urban/rural when possible)",
            "raster": "National wealth + uncertainty rasters sampled at cluster coordinates",
            "ins_crosscheck": "ECAM 4 regional indicators (public INS tables)",
            "limitation": (
                "Proxy validation — not substitute for partner field workshop. "
                "DHS wealth ≠ monetary poverty; cluster displacement ~2 km."
            ),
        },
        "metrics": metrics,
        "concordance_counts": counts,
        "ins_regional_metrics": ins_metrics,
        "sites": [asdict(s) for s in sites],
        "ethics": "exploratory_only_no_targeting_no_operational_use",
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Validation terrain proxy — Post-v1.0 Action 1",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC*",
        "",
        "## Méthodologie (données publiques)",
        "",
        "- **Référence terrain proxy :** `wealth_index` DHS 2018 aux centroides de grappes (430 clusters).",
        "- **Sites :** échantillon stratifié par région (+ urbain/rural si disponible).",
        "- **Carte :** échantillonnage des rasters nationaux richesse + incertitude (modèle v4).",
        "- **Validation externe :** concordance régionale INS ECAM 4 (déjà calculée).",
        "",
        "## Métriques clés",
        "",
        f"| Métrique | Valeur |",
        f"|----------|--------|",
        f"| Sites proxy | {int(metrics.get('n_sites', 0))} |",
        f"| Régions couvertes | {int(metrics.get('n_regions', 0))} |",
        f"| Spearman OOF vs DHS | {metrics.get('spearman_oof_vs_dhs', float('nan')):.3f} |",
        f"| Spearman raster vs DHS | {metrics.get('spearman_raster_vs_dhs', float('nan')):.3f} |",
        f"| MAE OOF | {metrics.get('mae_oof', float('nan')):.1f} |",
        f"| MAE raster | {metrics.get('mae_raster', float('nan')):.1f} |",
        f"| Concordance match | {metrics.get('concordance_match_pct', 0):.1f}% |",
        f"| Concordance mismatch | {metrics.get('concordance_mismatch_pct', 0):.1f}% |",
        "",
    ]
    if ins_metrics:
        lines.extend(
            [
                "## Cross-check INS ECAM 4 (régional)",
                "",
                f"- Spearman wealth vs pauvreté : **{ins_metrics.get('spearman_wealth_vs_poverty', float('nan')):.3f}**",
                f"- Écart rang moyen : {ins_metrics.get('mean_rank_gap', float('nan')):.2f}",
                "",
            ]
        )

    lines.extend(
        [
            "## Concordance bins (DHS vs carte)",
            "",
            f"| Type | n |",
            f"|------|---|",
            f"| match | {counts.get('match', 0)} |",
            f"| partial | {counts.get('partial', 0)} |",
            f"| mismatch | {counts.get('mismatch', 0)} |",
            "",
            "## Limites",
            "",
            "- Proxy numérique — **pas** de remplacement d'un atelier partenaire terrain.",
            "- Wealth DHS (actifs) ≠ pauvreté monétaire ECAM.",
            "- Déplacement GPS DHS (~2 km) peut expliquer des écarts locaux.",
            "- **Ne pas utiliser pour ciblage opérationnel.**",
            "",
            "## Suite recommandée",
            "",
            "- Atelier partenaire avec ≥5 sites réels (`partner_pack/field_data/sites.csv`).",
            "- Action 2 : intégration ECAM 5 lorsque micro-données publiques disponibles.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")