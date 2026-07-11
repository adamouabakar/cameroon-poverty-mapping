#!/usr/bin/env python
"""
Agent Résultats v4 — cartes nationales, diagnostics, rapport et notebook 03.

Usage :
  python scripts/generate_results_v4_visualizations.py
  python scripts/generate_results_v4_visualizations.py --skip-inference
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "outputs/reports"
MAPS_DIR = PROJECT_ROOT / "outputs/maps"
NOTEBOOK_OUT = PROJECT_ROOT / "notebooks/03_results_visualization.ipynb"
NOTEBOOK_EXEC = PROJECT_ROOT / "notebooks/03_results_visualization_executed.ipynb"

CLUSTERS = PROJECT_ROOT / "data/processed/dhs_clusters_real.parquet"
OOF = PROJECT_ROOT / "data/processed/training/oof_predictions.parquet"
V4_RESULTS = REPORTS_DIR / "model_v4_results.json"
WEALTH_V4 = MAPS_DIR / "wealth_index_predicted_1km_model_v4.tif"
UNC_V4 = MAPS_DIR / "wealth_uncertainty_1km_model_v4.tif"
PRIORITY_V4 = MAPS_DIR / "priority_index_1km_v4.tif"

REGIONAL_FOCUS = [
    "Adamaoua", "Extrême-Nord", "Centre", "Littoral", "Ouest",
    "Douala", "Nord-Ouest", "Nord", "Est", "Sud",
]


def _importance_dict(report: dict) -> dict:
    model_path = PROJECT_ROOT / report.get("artifacts", {}).get(
        "model", "models/wealth_model_lgbm_v0_gee_v4.pkl"
    )
    if model_path.exists():
        from src.models.save_load import load_model

        model = load_model(model_path)
        fi = model.feature_importance()
        return fi.set_index("feature")["gain"].to_dict()
    rows = report.get("top10_importance_v4", [])
    imp = {row["feature"]: row["gain"] for row in rows}
    for row in report.get("ins_feature_importance", []):
        imp[row["feature"]] = row["gain"]
    return imp


def _write_summary_md(report: dict, artifacts: dict) -> Path:
    m = report["metrics_v4_oof"]
    m3 = report["metrics_v3_oof"]
    delta = report["comparison_v3_vs_v4"]["metrics"]["delta_v4_minus_v3"]
    ins_src = report["ins_source"]

    lines = [
        "# Synthèse des résultats — Cartographie de la pauvreté, Cameroun",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "## Modèle v4 (DHS 2018 + GEE v3 + INS ECAM 4)",
        "",
        "Le modèle v4 combine **13 variables satellitaires/OSM** (GEE v3) et **4 indicateurs",
        "régionaux INS** issus de l'ECAM 4 (2014) : taux de pauvreté, alphabétisation,",
        "accès électricité et scolarisation primaire.",
        "",
        "### Métriques OOF (430 grappes)",
        "",
        "| Métrique | v3 (GEE) | v4 (GEE+INS) | Δ v4−v3 |",
        "|----------|----------|--------------|---------|",
        f"| R² | {m3['r2']:.4f} | {m['r2']:.4f} | {delta['r2']:+.4f} |",
        f"| Spearman | {m3['spearman']:.4f} | {m['spearman']:.4f} | {delta['spearman']:+.4f} |",
        f"| RMSE | {m3['rmse']:.0f} | {m['rmse']:.0f} | {delta['rmse']:+.0f} |",
        f"| MAE | {m3['mae']:.0f} | {m['mae']:.0f} | {delta['mae']:+.0f} |",
        "",
        f"- CV spatiale : **{report['cv_strategy']}** ({report['n_clusters']} grappes)",
        f"- Source INS : **{ins_src['survey']}** ({ins_src['year']}), {ins_src['producer']}",
        "",
        "## Rôle des variables INS",
        "",
        "| Variable INS | Interprétation |",
        "|--------------|----------------|",
        "| `ins_poverty_rate_pct` | Ancrage sur la pauvreté monétaire régionale officielle |",
        "| `ins_literacy_rate_15plus_pct` | Capital humain — corrélé au wealth DHS |",
        "| `ins_electricity_access_pct` | Proxy d'accès aux services de base |",
        "| `ins_primary_enrollment_pct` | Scolarisation — signal complémentaire en zones rurales |",
        "",
        "L'**alphabétisation INS** et la **luminosité nocturne** figurent parmi les variables",
        "les plus importantes du modèle v4. Les indicateurs INS améliorent modestement les",
        "métriques OOF (+0.007 R²) en captant la structure **régionale** non entièrement",
        "visible dans les seules images satellite.",
        "",
        "**Attention** : les variables INS sont **constantes par région DHS** — sur la carte",
        "nationale 1 km, elles sont assignées via la grappe DHS la plus proche. La carte",
        "montre surtout la variabilité **intra-régionale** portée par GEE, calibrée par le",
        "niveau régional INS.",
        "",
        "## Cartes produites",
        "",
        "| Carte | Fichier |",
        "|-------|---------|",
        f"| Wealth national v4 | `outputs/maps/wealth_index_predicted_1km_model_v4.tif` |",
        f"| Incertitude v4 | `outputs/maps/wealth_uncertainty_1km_model_v4.tif` |",
        f"| Priorisation v4 | `outputs/maps/priority_index_1km_v4.tif` |",
        f"| Grappes OOF v4 | `outputs/maps/wealth_national_clusters_v4.png` |",
        "",
        "## Limites",
        "",
    ]
    skip = "raster national v4 non disponible"
    for lim in report.get("limitations", []):
        if skip in lim.lower():
            continue
        lines.append(f"- {lim}")
    lines.extend([
        "- Jitter DHS (~2 km) : les buffers de grappes ne localisent pas les ménages exactement.",
        "- ECAM 4 (2014) vs DHS 2018 : décalage temporel de 4 ans.",
        "- Carte raster v4 : pas de micro-données INS infra-régionales.",
        "",
        "## Recommandations politiques",
        "",
        "1. **Prioriser** les zones à faible wealth prédit *et* forte incertitude (Extrême-Nord,",
        "   Adamaoua rural) pour enquêtes de validation terrain.",
        "2. **Croiser** la carte de priorisation avec les programmes existants (électrification,",
        "   écoles, santé) pour éviter les doublons d'intervention.",
        "3. **Poursuivre** le partenariat INS pour ECAM 5 (2022) et données infra-régionales.",
        "4. Ne pas utiliser ces cartes comme **seul** critère d'allocation budgétaire sans",
        "   validation locale.",
        "",
        "## Visualisations",
        "",
        "| Artefact | Chemin |",
        "|----------|--------|",
    ])
    for name, path in sorted(artifacts.items()):
        try:
            rel = Path(path).relative_to(PROJECT_ROOT)
        except ValueError:
            rel = path
        lines.append(f"| {name} | `{rel}` |")

    lines.extend([
        "",
        "## Prochaines étapes (Phase 5 — Documentation finale)",
        "",
        "1. Rapport technique bilingue (méthode, limites, protocole de validation terrain)",
        "2. Mise à jour README / REPRODUCIBILITY avec pipeline v4 complet",
        "3. Publication open-source et partage avec partenaires camerounais (INS, MINPLADAT)",
        "4. Pilote transposition autre pays DHS (`documentation/transposition_guide.md`)",
        "",
    ])

    out = REPORTS_DIR / "final_results_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _build_notebook() -> None:
    import nbformat as nbf

    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(
            "# Notebook 03 — Visualisation des résultats (v4)\n\n"
            "Cartographie de la pauvreté au Cameroun : DHS 2018, GEE v3, INS ECAM 4."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "import json\n"
            "from IPython.display import Image, display, Markdown\n\n"
            "_cwd = Path.cwd()\n"
            "PROJECT_ROOT = _cwd if (_cwd / 'outputs').exists() else _cwd.parent\n"
            "REPORTS = PROJECT_ROOT / 'outputs/reports'\n"
            "MAPS = PROJECT_ROOT / 'outputs/maps'\n"
            "report = json.loads((REPORTS / 'model_v4_results.json').read_text())\n"
            "m = report['metrics_v4_oof']\n"
            "print(f\"R² OOF v4: {m['r2']:.4f}\")\n"
            "print(f\"Spearman v4: {m['spearman']:.4f}\")"
        ),
        nbf.v4.new_markdown_cell("## Diagnostic modèle v4"),
        nbf.v4.new_code_cell(
            "plots = [\n"
            "    'oof_scatter_v4.png', 'residuals_v4.png',\n"
            "    'feature_importance_v4_top17.png', 'v3_vs_v4_metrics_viz.png',\n"
            "]\n"
            "for name in plots:\n"
            "    p = REPORTS / name\n"
            "    if p.exists():\n"
            "        display(Markdown(f'### {name}'))\n"
            "        display(Image(filename=str(p)))"
        ),
        nbf.v4.new_markdown_cell("## Cartes nationales v4"),
        nbf.v4.new_code_cell(
            "for name in [\n"
            "    'wealth_index_predicted_1km_model_v4.png',\n"
            "    'wealth_uncertainty_1km_model_v4.png',\n"
            "    'priority_index_1km_v4.png',\n"
            "    'wealth_national_clusters_v4.png',\n"
            "]:\n"
            "    p = MAPS / name\n"
            "    if p.exists():\n"
            "        display(Markdown(f'### {name}'))\n"
            "        display(Image(filename=str(p)))"
        ),
        nbf.v4.new_markdown_cell("## Cartes régionales"),
        nbf.v4.new_code_cell(
            "for sub in ['regional', 'regional_v4']:\n"
            "    reg_dir = MAPS / sub\n"
            "    if reg_dir.exists():\n"
            "        for p in sorted(reg_dir.glob('*.png')):\n"
            "            display(Markdown(f'### {p.name}'))\n"
            "            display(Image(filename=str(p)))"
        ),
        nbf.v4.new_markdown_cell(
            "## Rapport\n\nVoir `outputs/reports/final_results_summary.md`"
        ),
    ]
    NOTEBOOK_OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, NOTEBOOK_OUT.open("w", encoding="utf-8"))


def _execute_notebook() -> None:
    import nbformat
    from nbclient import NotebookClient

    nb = nbformat.read(NOTEBOOK_OUT, as_version=4)
    client = NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        resources={"path": str(NOTEBOOK_OUT.parent)},
    )
    client.execute()
    nbformat.write(nb, NOTEBOOK_EXEC.open("w", encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Visualisations et rapport v4")
    p.add_argument("--skip-inference", action="store_true")
    p.add_argument("--skip-notebook-exec", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not V4_RESULTS.exists():
        print(f"❌ Rapport v4 introuvable : {V4_RESULTS}")
        print("   Lancez : python scripts/run_model_v4_evaluation.py")
        return 1

    if not args.skip_inference:
        print("▶ Inférence nationale v4…")
        subprocess.check_call(
            [sys.executable, str(PROJECT_ROOT / "scripts/run_national_inference_v4.py")],
            cwd=PROJECT_ROOT,
        )

    if not WEALTH_V4.exists():
        print(f"❌ Raster wealth v4 absent : {WEALTH_V4}")
        return 1

    import geopandas as gpd
    import pandas as pd

    from src.models.uncertainty_raster import export_uncertainty_on_wealth_grid
    from src.simulation.priority_raster import compute_priority_raster
    from src.visualization.results_plots import (
        plot_feature_importance,
        plot_oof_scatter,
        plot_residuals,
        plot_v3_v4_metrics,
    )
    from src.visualization.static_maps import (
        merge_oof_with_clusters,
        plot_cluster_choropleth,
        plot_regional_maps,
        plot_regional_raster_maps,
        plot_raster_preview,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    report = json.loads(V4_RESULTS.read_text(encoding="utf-8"))
    oof_df = pd.read_parquet(OOF)
    clusters = gpd.read_parquet(CLUSTERS)
    gdf = merge_oof_with_clusters(clusters, oof_df)
    metrics = report["metrics_v4_oof"]
    importance = _importance_dict(report)

    artifacts: dict[str, str] = {}

    # Diagnostics
    p = REPORTS_DIR / "oof_scatter_v4.png"
    plot_oof_scatter(oof_df, metrics, p)
    artifacts["scatter_oof_v4"] = str(p)

    p = REPORTS_DIR / "residuals_v4.png"
    plot_residuals(oof_df, p)
    artifacts["residuals_v4"] = str(p)

    p = REPORTS_DIR / "feature_importance_v4_top17.png"
    plot_feature_importance(
        importance, p, top_n=17,
        title="Top 17 — importance v4 (GEE + INS)",
    )
    artifacts["importance_v4"] = str(p)

    p = REPORTS_DIR / "v3_vs_v4_metrics_viz.png"
    plot_v3_v4_metrics(V4_RESULTS, p)
    artifacts["v3_vs_v4"] = str(p)

    # Cartes grappes OOF
    vmin = gdf["y_oof_pred"].quantile(0.05)
    vmax = gdf["y_oof_pred"].quantile(0.95)

    p = MAPS_DIR / "wealth_national_clusters_v4.png"
    plot_cluster_choropleth(
        gdf, "y_oof_pred", p,
        title="Cameroun — wealth index prédit OOF v4 (buffers DHS)",
        vmin=vmin, vmax=vmax,
    )
    artifacts["map_clusters_v4"] = str(p)

    p = MAPS_DIR / "uncertainty_national_clusters_v4.png"
    plot_cluster_choropleth(
        gdf, "uncertainty_half_width", p,
        title="Cameroun — incertitude OOF v4 (demi-intervalle 90 %)",
        cmap="Purples",
    )
    artifacts["map_uncertainty_clusters_v4"] = str(p)

    regional_dir = MAPS_DIR / "regional_v4"
    regional_paths = plot_regional_maps(
        gdf, "y_oof_pred", REGIONAL_FOCUS, regional_dir,
    )
    for rp in regional_paths:
        artifacts[f"regional_cluster_{rp.stem}"] = str(rp)

    # Incertitude raster v4
    print("▶ Incertitude raster v4…")
    export_uncertainty_on_wealth_grid(WEALTH_V4, clusters, oof_df, UNC_V4)
    unc_png = MAPS_DIR / "wealth_uncertainty_1km_model_v4.png"
    plot_raster_preview(
        UNC_V4, unc_png,
        title="Incertitude OOF — grille modèle v4 (1 km)",
        cmap="Purples",
        colorbar_label="Demi-largeur intervalle 90 %",
    )
    artifacts["uncertainty_raster_v4"] = str(UNC_V4)
    artifacts["uncertainty_preview_v4"] = str(unc_png)

    # Priorisation v4
    features_raster = PROJECT_ROOT / "data/processed/rasters/cm_features_1km_v3.tif"
    criteria = PROJECT_ROOT / "configs/prioritization_criteria.yaml"
    if features_raster.exists() and criteria.exists():
        print("▶ Priorisation v4…")
        compute_priority_raster(WEALTH_V4, features_raster, criteria, PRIORITY_V4)
        pri_png = MAPS_DIR / "priority_index_1km_v4.png"
        plot_raster_preview(
            PRIORITY_V4, pri_png,
            title="Zones prioritaires — indice composite v4 (1 km)",
            cmap="YlOrRd",
            colorbar_label="Indice de priorisation (0–1)",
        )
        artifacts["priority_raster_v4"] = str(PRIORITY_V4)
        artifacts["priority_preview_v4"] = str(pri_png)

    # Cartes raster régionales
    raster_regional = plot_regional_raster_maps(
        WEALTH_V4, clusters, REGIONAL_FOCUS, regional_dir,
    )
    for rp in raster_regional:
        artifacts[f"regional_raster_{rp.stem}"] = str(rp)

    artifacts["wealth_raster_v4"] = str(WEALTH_V4)
    artifacts["wealth_preview_v4"] = str(MAPS_DIR / "wealth_index_predicted_1km_model_v4.png")

    summary_path = _write_summary_md(report, artifacts)
    artifacts["final_summary"] = str(summary_path)

    _build_notebook()
    if not args.skip_notebook_exec:
        print("▶ Exécution notebook 03…")
        _execute_notebook()
        artifacts["notebook_executed"] = str(NOTEBOOK_EXEC)

    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_set": "v4",
        "artifacts": artifacts,
        "metrics_v4_oof": metrics,
    }
    manifest_path = REPORTS_DIR / "visualization_v4_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    sync_script = PROJECT_ROOT / "scripts/sync_figures.py"
    if sync_script.exists():
        subprocess.call([sys.executable, str(sync_script)], cwd=PROJECT_ROOT)

    print("✅ Visualisations v4 générées")
    print(f"   Rapport : {summary_path}")
    print(f"   Notebook : {NOTEBOOK_OUT}")
    if NOTEBOOK_EXEC.exists():
        print(f"   Exécuté : {NOTEBOOK_EXEC}")
    print(f"   Cartes : {MAPS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())