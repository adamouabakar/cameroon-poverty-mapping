#!/usr/bin/env python
"""
Génère visualisations, cartes et rapport de synthèse (Agent Résultats).

Usage :
  python scripts/generate_results_visualizations.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "outputs/reports"
MAPS_DIR = PROJECT_ROOT / "outputs/maps"
NOTEBOOK_OUT = PROJECT_ROOT / "notebooks/03_results_visualization.ipynb"

CLUSTERS = PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet"
OOF = PROJECT_ROOT / "data/processed/training/oof_predictions.parquet"
REAL_RESULTS = REPORTS_DIR / "real_model_results.json"
IMPORTANCE = REPORTS_DIR / "feature_importance_gain_real.csv"

REGIONAL_FOCUS = [
    "Adamaoua", "Extrême-Nord", "Centre", "Douala", "Nord-Ouest", "Littoral",
]


def _write_summary_md(report: dict, artifacts: dict) -> Path:
    m = report["metrics_oof"]
    top = report["top10_importance"][:5]
    comp = report["comparison"]
    lines = [
        "# Synthèse des résultats — Cartographie de la pauvreté, Cameroun 2018",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Métriques OOF (v3, 430 grappes réelles)",
        "",
        "| Métrique | Valeur |",
        "|----------|--------|",
        f"| R² OOF | {m['r2']:.4f} |",
        f"| Spearman OOF | {m['spearman']:.4f} |",
        f"| RMSE OOF | {m['rmse']:.0f} |",
        f"| MAE OOF | {m['mae']:.0f} |",
        f"| CV | {report['cv_strategy']} |",
        "",
        "## Features les plus importantes",
        "",
        "| Rang | Feature | Type |",
        "|------|---------|------|",
    ]
    for row in report["top10_importance"][:10]:
        f = row["feature"]
        ftype = "CHIRPS" if "precip" in f else ("GHSL" if f == "ghsl_built_fraction" else "Base/OSM")
        lines.append(f"| {row['rank']} | `{f}` | {ftype} |")

    lines.extend([
        "",
        "## Interprétation",
        "",
        "- **Luminosité nocturne** et **densité de population** captent l'urbanisation et l'accès aux services.",
        "- **GHSL** (surface bâtie) corrèle fortement avec le wealth index (r ≈ 0.74).",
        "- **CHIRPS** (`precip_annual_mm`) est la 2ᵉ feature en importance — le climat structure le bien-être rural.",
        "- Les **distances** (routes, écoles, santé) reflètent l'accès aux infrastructures.",
        "",
        "## Comparaison v2 vs v3 (données réelles)",
        "",
        f"- Δ R² (v3 − v2) : **{comp['v2_vs_v3_real']['delta_r2_v3_minus_v2']:+.3f}**",
        f"- Δ Spearman : **{comp['v2_vs_v3_real']['delta_spearman']:+.3f}**",
        "",
        "## Limites",
        "",
    ])
    for lim in report["assessment"]["limits"]:
        lines.append(f"- {lim}")
    lines.extend([
        "",
        "## Visualisations",
        "",
        "| Fichier | Description |",
        "|---------|-------------|",
    ])
    for name, path in sorted(artifacts.items()):
        try:
            rel = Path(path).relative_to(PROJECT_ROOT)
        except ValueError:
            rel = path
        lines.append(f"| {name} | `{rel}` |")
    lines.extend([
        "",
        "## Prochaines étapes",
        "",
        "1. Export GEE national des features → inférence `run_national_inference.py --mode raster`",
        "2. Documentation finale (méthodologie, limitations, guide utilisateur)",
        "3. Publication open-source (README, DOI données DHS)",
        "",
    ])
    out = REPORTS_DIR / "final_results_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _build_notebook(artifacts: dict) -> None:
    import nbformat as nbf

    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(
            "# Notebook 03 — Visualisation des résultats\n\n"
            "Cartographie de la pauvreté au Cameroun (DHS 2018, features GEE v3)."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "import json\n"
            "import geopandas as gpd\n"
            "import pandas as pd\n"
            "from IPython.display import Image, display, Markdown\n\n"
            "PROJECT_ROOT = Path('..').resolve()\n"
            "REPORTS = PROJECT_ROOT / 'outputs/reports'\n"
            "MAPS = PROJECT_ROOT / 'outputs/maps'\n"
            "report = json.loads((REPORTS / 'real_model_results.json').read_text())\n"
            "print('R² OOF:', report['metrics_oof']['r2'])\n"
            "print('Spearman:', report['metrics_oof']['spearman'])"
        ),
        nbf.v4.new_markdown_cell("## Diagnostic modèle"),
        nbf.v4.new_code_cell(
            "for name in ['oof_scatter_viz.png', 'residuals_oof.png', "
            "'feature_importance_top15.png', 'metrics_comparison.png']:\n"
            "    p = REPORTS / name\n"
            "    if p.exists():\n"
            "        display(Markdown(f'### {name}'))\n"
            "        display(Image(filename=str(p)))"
        ),
        nbf.v4.new_markdown_cell("## Cartes nationales et régionales"),
        nbf.v4.new_code_cell(
            "for name in ['wealth_national_clusters.png', 'uncertainty_national_clusters.png',\n"
            "             'wealth_index_predicted_1km.png', 'wealth_uncertainty_1km.png']:\n"
            "    p = MAPS / name\n"
            "    if p.exists():\n"
            "        display(Markdown(f'### {name}'))\n"
            "        display(Image(filename=str(p)))\n"
            "reg_dir = MAPS / 'regional'\n"
            "if reg_dir.exists():\n"
            "    for p in sorted(reg_dir.glob('*.png')):\n"
            "        display(Markdown(f'### {p.name}'))\n"
            "        display(Image(filename=str(p)))"
        ),
        nbf.v4.new_markdown_cell(
            "## Rapport\n\n"
            "Voir `outputs/reports/final_results_summary.md`"
        ),
    ]
    NOTEBOOK_OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK_OUT.open("w", encoding="utf-8"))


def main() -> int:
    import geopandas as gpd
    import pandas as pd

    from src.visualization.results_plots import (
        plot_feature_importance,
        plot_metrics_comparison,
        plot_oof_scatter,
        plot_residuals,
    )
    from src.visualization.static_maps import (
        merge_oof_with_clusters,
        plot_cluster_choropleth,
        plot_regional_maps,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    report = json.loads(REAL_RESULTS.read_text(encoding="utf-8"))
    oof_df = pd.read_parquet(OOF)
    clusters = gpd.read_parquet(CLUSTERS)
    gdf = merge_oof_with_clusters(clusters, oof_df)

    if "importance_gain" in report:
        imp = report["importance_gain"]
    else:
        imp_df = pd.read_csv(IMPORTANCE)
        imp = imp_df.set_index("feature")["gain"].to_dict()
    metrics = report["metrics_oof"]

    artifacts = {}

    p = REPORTS_DIR / "oof_scatter_viz.png"
    plot_oof_scatter(oof_df, metrics, p)
    artifacts["scatter_oof"] = str(p)

    p = REPORTS_DIR / "residuals_oof.png"
    plot_residuals(oof_df, p)
    artifacts["residuals"] = str(p)

    p = REPORTS_DIR / "feature_importance_top15.png"
    plot_feature_importance(imp, p, top_n=15, title="Top 15 — importance (données réelles v3)")
    artifacts["importance_top15"] = str(p)

    p = REPORTS_DIR / "metrics_comparison.png"
    plot_metrics_comparison(REAL_RESULTS, p)
    artifacts["metrics_comparison"] = str(p)

    vmin = gdf["y_oof_pred"].quantile(0.05)
    vmax = gdf["y_oof_pred"].quantile(0.95)

    p = MAPS_DIR / "wealth_national_clusters.png"
    plot_cluster_choropleth(
        gdf, "y_oof_pred", p,
        title="Cameroun — wealth index prédit (OOF, buffers DHS)",
        vmin=vmin, vmax=vmax,
    )
    artifacts["map_clusters_wealth"] = str(p)

    p = MAPS_DIR / "uncertainty_national_clusters.png"
    plot_cluster_choropleth(
        gdf, "uncertainty_half_width", p,
        title="Cameroun — incertitude OOF (demi-intervalle 90 %)",
        cmap="Purples",
    )
    artifacts["map_clusters_uncertainty"] = str(p)

    regional_paths = plot_regional_maps(
        gdf, "y_oof_pred", REGIONAL_FOCUS, MAPS_DIR / "regional",
    )
    for rp in regional_paths:
        artifacts[f"regional_{rp.stem}"] = str(rp)

    # Grille nationale interpolée 1 km
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_national_inference",
        PROJECT_ROOT / "scripts/run_national_inference.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    inf = mod.run_interpolate()
    artifacts["wealth_raster"] = inf["wealth_raster"]
    artifacts["uncertainty_raster"] = inf["uncertainty_raster"]

    summary_path = _write_summary_md(report, artifacts)
    artifacts["final_summary"] = str(summary_path)
    _build_notebook(artifacts)

    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
        "metrics_oof": metrics,
    }
    manifest_path = REPORTS_DIR / "visualization_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Visualisations générées")
    print(f"   Rapport : {summary_path}")
    print(f"   Notebook : {NOTEBOOK_OUT}")
    print(f"   Cartes : {MAPS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())