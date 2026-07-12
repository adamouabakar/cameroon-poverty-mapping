#!/usr/bin/env python
"""
Jalon 6 — Modèle spatio-temporel + animation temporelle.

Usage:
  python scripts/run_jalon6_modele_temporel.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import geopandas as gpd
import pandas as pd

from src.temporal.animate import export_temporal_web_assets, plot_regional_temporal_gif
from src.temporal.panel_model import build_temporal_panel, compute_temporal_metrics


def main() -> int:
    clusters = gpd.read_parquet(PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet")
    oof = pd.read_parquet(PROJECT_ROOT / "data/processed/training/oof_predictions.parquet")

    panel = build_temporal_panel(clusters, oof, project_root=PROJECT_ROOT)
    metrics = compute_temporal_metrics(panel)

    panel_path = PROJECT_ROOT / "data/processed/temporal/cluster_wealth_panel.parquet"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(panel_path, index=False)

    gif_path = PROJECT_ROOT / "outputs/maps/temporal_wealth_animation.gif"
    plot_regional_temporal_gif(panel, gif_path)

    json_path = export_temporal_web_assets(panel, PROJECT_ROOT / "site/assets")

    report = {
        "jalon": 6,
        "title": "Modèle spatio-temporel + animation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "deliverables": {
            "panel_parquet": str(panel_path.relative_to(PROJECT_ROOT)),
            "temporal_gif": str(gif_path.relative_to(PROJECT_ROOT)),
            "web_json": str(json_path.relative_to(PROJECT_ROOT)),
            "temporal_page": "site/temporal.html",
            "agent_spec": "src/agents/jalons/jalon6_modele_temporel.md",
        },
        "metrics": metrics,
        "methodology": {
            "years": [2014, 2018, 2022],
            "anchor": "OOF 2018 + ajustements pauvreté INS ECAM4/ECAM5 par région",
            "data_sources": [
                "data/reference/ins/ecam4_regional_indicators.csv",
                "data/reference/ins/ecam5_regional_indicators.csv",
                "data/processed/dhs_clusters_real.parquet",
            ],
        },
        "next_jalon": 7,
    }
    report_path = PROJECT_ROOT / "outputs/reports/jalon6_temporal_model.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Jalon 6 terminé — modèle spatio-temporel")
    print(f"  Panel : {panel_path} ({len(panel)} lignes)")
    print(f"  GIF   : {gif_path}")
    print(f"  Web   : {json_path}")
    print(f"  Rapport : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())