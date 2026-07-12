#!/usr/bin/env python
"""
Post-v1.0 Action 4 — Cartes + actionnabilité.

- Régénère cartes v4 (sans ré-inférence lourde)
- Priorisation raster « actionable »
- Indice actionnabilité grappes (v5_post + OOF uncertainty)
- Rapport décisionnel mis à jour
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import pandas as pd

from src.simulation.actionability import compute_actionability_index, top_actionable_zones
from src.simulation.prioritization import load_prioritization_config
from src.simulation.priority_raster import compute_priority_raster
from src.visualization.static_maps import plot_raster_preview


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post-v1 Action 4 — maps + actionability")
    p.add_argument("--skip-map-regen", action="store_true")
    p.add_argument("--top-n", type=int, default=30)
    return p.parse_args()


def _build_cluster_actionability(top_n: int) -> tuple[pd.DataFrame, list[dict]]:
    clusters = gpd.read_parquet(PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet")
    oof = pd.read_parquet(PROJECT_ROOT / "data/processed/training/oof_predictions.parquet")
    features = pd.read_parquet(
        PROJECT_ROOT / "data/processed/features/cluster_features_v5_post.parquet"
    )

    merged = clusters.merge(oof, on="cluster_id", how="inner")
    merged = merged.merge(features, on="cluster_id", how="inner", suffixes=("", "_feat"))
    merged["predicted_wealth"] = merged["y_oof_pred"]
    merged["uncertainty_width"] = (merged["upper_90"] - merged["lower_90"]).abs()

    criteria = load_prioritization_config(
        PROJECT_ROOT / "configs/prioritization_criteria_actionable.yaml"
    )
    ranked = compute_actionability_index(
        merged,
        priority_weights=criteria["weights"],
    )
    top = top_actionable_zones(ranked, top_n=top_n)

    rows = []
    for _, row in top.iterrows():
        rows.append(
            {
                "cluster_id": int(row["cluster_id"]),
                "region": str(row.get("region", "")),
                "urban_rural": str(row.get("urban_rural", "")),
                "actionability_index": round(float(row["actionability_index"]), 4),
                "priority_index": round(float(row["priority_index"]), 4),
                "predicted_wealth": round(float(row["predicted_wealth"]), 2),
                "accessibility_inverse": round(float(row.get("accessibility_inverse", 0)), 4),
                "uncertainty_width": round(float(row.get("uncertainty_width", 0)), 2),
                "lat": round(float(row["latitude"]), 5),
                "lon": round(float(row["longitude"]), 5),
            }
        )
    return ranked, rows


def _update_decision_report(v5_report: dict, action_rows: list[dict]) -> Path:
    ins_path = PROJECT_ROOT / "outputs/reports/post_v1_action2_ecam5.json"
    ins_spearman = None
    if ins_path.is_file():
        ins_spearman = json.loads(ins_path.read_text(encoding="utf-8")).get(
            "metrics_ecam5", {}
        ).get("spearman_wealth_vs_poverty")

    m = v5_report.get("metrics_v5_post_oof", {})
    top3 = action_rows[:3]
    rows_html = "".join(
        f"<tr><td>{r['region']}</td><td>{r['cluster_id']}</td>"
        f"<td>{r['actionability_index']}</td></tr>"
        for r in top3
    )
    ins_line = (
        f"<p>Spearman wealth ↔ pauvreté ECAM5 : <strong>{ins_spearman:.3f}</strong></p>"
        if ins_spearman is not None
        else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"/><title>Rapport décisionnel v5_post</title>
<style>body{{font-family:system-ui;max-width:800px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:0.5rem}}</style></head>
<body>
<h1>Rapport décisionnel — Post-v1.0 Action 4</h1>
<p><em>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</em></p>
<h2>Modèle v5_post (production candidate)</h2>
<table><tr><th>Métrique</th><th>Valeur</th></tr>
<tr><td>R² OOF</td><td>{m.get('r2', 0):.4f}</td></tr>
<tr><td>Spearman</td><td>{m.get('spearman', 0):.4f}</td></tr>
<tr><td>RMSE</td><td>{m.get('rmse', 0):.0f}</td></tr></table>
{ins_line}
<h2>Top zones actionnables (grappes)</h2>
<table><tr><th>Région</th><th>Cluster</th><th>Actionnabilité</th></tr>
{rows_html}</table>
<h2>Recommandations</h2>
<ul>
<li>Croiser wealth, priorité et incertitude avant décision.</li>
<li>Prioriser validation terrain sur grappes à fort indice actionnabilité.</li>
<li>Usage exploratoire uniquement — pas de ciblage ménage/village.</li>
</ul>
<p><a href="https://adamouabakar.github.io/cameroon-poverty-mapping/">Carte interactive</a></p>
</body></html>"""

    out = PROJECT_ROOT / "outputs/reports/decision_report_v5_post.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def main() -> int:
    args = parse_args()

    if not args.skip_map_regen:
        subprocess.check_call(
            [sys.executable, str(PROJECT_ROOT / "scripts/make_maps.py"), "--skip-notebook"],
            cwd=PROJECT_ROOT,
        )

    criteria_path = PROJECT_ROOT / "configs/prioritization_criteria_actionable.yaml"
    criteria = load_prioritization_config(criteria_path)
    wealth_path = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model_v4.tif"
    features_path = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
    if not wealth_path.is_file():
        wealth_path = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model.tif"

    out_cfg = criteria.get("output", {})
    priority_tif = PROJECT_ROOT / out_cfg.get(
        "priority_raster", "outputs/maps/priority_index_1km_actionable.tif"
    )
    priority_png = PROJECT_ROOT / out_cfg.get(
        "priority_preview", "outputs/maps/priority_index_1km_actionable.png"
    )

    compute_priority_raster(wealth_path, features_path, criteria_path, priority_tif)
    plot_raster_preview(
        priority_tif,
        priority_png,
        title="Indice de priorisation actionnable (1 km) — Post-v1",
        cmap="YlOrRd",
    )

    _, action_rows = _build_cluster_actionability(top_n=args.top_n)

    v5_path = PROJECT_ROOT / "outputs/reports/post_v1_action3_model_v5.json"
    v5_report = {}
    if v5_path.is_file():
        v5_report = json.loads(v5_path.read_text(encoding="utf-8"))

    decision_html = _update_decision_report(v5_report, action_rows)

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "action": "post_v1_action4_maps",
        "artifacts": {
            "priority_raster_actionable": str(priority_tif.relative_to(PROJECT_ROOT)),
            "priority_preview_actionable": str(priority_png.relative_to(PROJECT_ROOT)),
            "decision_report": str(decision_html.relative_to(PROJECT_ROOT)),
            "wealth_raster_used": str(wealth_path.relative_to(PROJECT_ROOT)),
        },
        "top_actionable_clusters": action_rows,
        "criteria_weights": criteria["weights"],
        "note": "Indice actionnabilité = priorité × accessibilité × confiance OOF (exploratoire).",
    }
    report_path = PROJECT_ROOT / "outputs/reports/post_v1_action4_actionability.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = PROJECT_ROOT / "outputs/reports/post_v1_action4_actionability.md"
    md_path.write_text(
        "\n".join(
            [
                "# Post-v1.0 Action 4 — Cartes + actionnabilité",
                "",
                f"- Priorité raster : `{priority_tif.name}`",
                f"- Top grappes actionnables : {len(action_rows)}",
                f"- Rapport HTML : `{decision_html.name}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print("✅ Post-v1 Action 4 — cartes + actionnabilité terminées")
    print(f"  Priorité : {priority_tif}")
    print(f"  Actionnabilité : {report_path}")
    print(f"  Décision : {decision_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())