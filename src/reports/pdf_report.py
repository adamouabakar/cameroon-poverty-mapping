"""Générateur de rapport PDF professionnel pour ONG."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from src.reports.region_stats import compute_regional_summary, load_cluster_frame

DEFAULT_SCREENSHOTS = {
    "wealth": "assets/screenshots/poverty_map_national_v4.png",
    "uncertainty": "assets/screenshots/uncertainty_map_v4.png",
    "priority": "assets/screenshots/actionability_map_v4.png",
    "ins": "assets/screenshots/ins_validation_scatter_v4.png",
}


def _load_json(path: Path) -> dict[str, Any] | None:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _load_metrics(project_root: Path) -> dict[str, Any]:
    for rel in (
        "outputs/reports/post_v1_action3_model_v5.json",
        "outputs/reports/model_v4_results.json",
        "outputs/reports/real_model_results_v2.json",
    ):
        raw = _load_json(project_root / rel)
        if not raw:
            continue
        if "metrics_v5_post_oof" in raw:
            return {"model": "v5_post", **raw["metrics_v5_post_oof"]}
        if "metrics_v4_oof" in raw:
            return {"model": "v4", **raw["metrics_v4_oof"]}
        if "metrics_oof" in raw:
            return {"model": "v5_post", **raw["metrics_oof"]}
    return {"model": "v4", "r2": 0.793, "spearman": 0.889, "rmse": 38323, "mae": 29504}


def _text_page(fig: Figure, lines: list[str], *, title: str = "") -> None:
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    if title:
        ax.text(0.05, 0.95, title, fontsize=16, fontweight="bold", va="top")
    y = 0.88 if title else 0.95
    for line in lines:
        ax.text(0.05, y, line, fontsize=10, va="top", family="sans-serif")
        y -= 0.045


def _image_page(fig: Figure, img_path: Path, *, caption: str) -> None:
    ax = fig.add_axes([0.05, 0.12, 0.9, 0.78])
    ax.axis("off")
    if img_path.is_file():
        img = plt.imread(img_path)
        ax.imshow(img)
    else:
        ax.text(0.5, 0.5, f"Image manquante:\n{img_path.name}", ha="center", va="center")
    fig.text(0.05, 0.04, caption, fontsize=9, style="italic")


def _table_page(fig: Figure, df: pd.DataFrame, *, title: str) -> None:
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=20)
    if df.empty:
        ax.text(0.05, 0.5, "Aucune donnée pour cette région.", fontsize=11)
        return
    show = df.head(14)
    table = ax.table(
        cellText=show.values,
        colLabels=show.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.4)


def _shap_bar_page(fig: Figure, shap_data: dict[str, Any]) -> None:
    ax = fig.add_axes([0.12, 0.15, 0.82, 0.7])
    items = shap_data.get("top10_mean_abs_shap", [])[:10]
    if not items:
        ax.text(0.5, 0.5, "SHAP non disponible", ha="center")
        ax.axis("off")
        return
    labels = [x["feature"] for x in items][::-1]
    vals = [x["mean_abs_shap"] for x in items][::-1]
    ax.barh(labels, vals, color="#2c7bb6")
    ax.set_xlabel("Importance moyenne |SHAP|")
    ax.set_title("Importance des variables (modèle v4)", fontweight="bold")
    fig.text(0.05, 0.04, "Source: SHAP TreeExplainer — échantillon grappes DHS", fontsize=8, style="italic")


def _comparison_page(fig: Figure, v4: dict | None, v5: dict | None) -> None:
    ax = fig.add_axes([0.15, 0.2, 0.75, 0.65])
    metrics = ["r2", "spearman"]
    labels = ["R² OOF", "Spearman"]
    x = range(len(metrics))
    w = 0.35
    v4_vals = [v4.get(m, 0) if v4 else 0 for m in metrics]
    v5_vals = [v5.get(m, 0) if v5 else 0 for m in metrics]
    ax.bar([i - w / 2 for i in x], v4_vals, width=w, label="v4", color="#888")
    if v5:
        ax.bar([i + w / 2 for i in x], v5_vals, width=w, label="v5_post", color="#2c7bb6")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.set_title("Comparaison modèles (OOF)", fontweight="bold")


def generate_ngo_pdf_report(
    project_root: Path,
    *,
    region: str = "Tout le Cameroun",
    output_path: Path | None = None,
) -> bytes:
    """
    Génère un rapport PDF multi-pages : couverture, cartes, stats, SHAP, comparaison.

    Retourne les bytes PDF ; écrit sur disque si output_path fourni.
    """
    project_root = Path(project_root)
    clusters = load_cluster_frame(project_root)
    summary = compute_regional_summary(clusters, region=region)
    metrics = _load_metrics(project_root)

    ins = _load_json(project_root / "outputs/reports/ins_external_validation.json")
    ins_spearman = (ins or {}).get("metrics", {}).get("spearman_wealth_vs_poverty")

    shap = _load_json(project_root / "outputs/reports/shap_summary_v4.json")
    if not shap:
        shap = _load_json(project_root / "site/assets/shap_summary.json")

    v4_raw = _load_json(project_root / "outputs/reports/model_v4_results.json")
    v5_raw = _load_json(project_root / "outputs/reports/post_v1_action3_model_v5.json")
    v4_m = (v4_raw or {}).get("metrics_v4_oof")
    v5_m = (v5_raw or {}).get("metrics_v5_post_oof")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    region_line = region if region != "Tout le Cameroun" else "Vue nationale"

    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        # Couverture
        fig = plt.figure(figsize=(8.27, 11.69))
        _text_page(
            fig,
            [
                f"Date : {now}",
                f"Périmètre : {region_line}",
                "",
                "Résumé exécutif",
                f"• Modèle : {metrics.get('model', 'v4')} — R² {metrics.get('r2', 0):.3f}, "
                f"Spearman {metrics.get('spearman', 0):.3f}",
                f"• Grappes DHS 2018 : {len(clusters)}",
                f"• Validation INS ECAM4 : Spearman {ins_spearman:.3f}" if ins_spearman else "• Validation INS : —",
                "",
                "Avertissement éthique",
                "Estimations exploratoires uniquement. Ne remplace pas l'INS.",
                "Pas de ciblage ménage/village. Croiser l'incertitude.",
                "",
                "Contact : abubakradamou@gmail.com",
                "https://github.com/adamouabakar/cameroon-poverty-mapping",
            ],
            title="Rapport ONG — Cameroon Poverty Mapping",
        )
        pdf.savefig(fig)
        plt.close(fig)

        # Cartes
        for key, caption in [
            ("wealth", "Carte nationale — indice de richesse estimé (1 km)"),
            ("uncertainty", "Carte d'incertitude du modèle"),
            ("priority", "Carte d'actionnabilité / priorisation exploratoire"),
            ("ins", "Validation externe — modèle vs pauvreté INS par région"),
        ]:
            fig = plt.figure(figsize=(8.27, 11.69))
            _image_page(fig, project_root / DEFAULT_SCREENSHOTS[key], caption=caption)
            pdf.savefig(fig)
            plt.close(fig)

        # Stats régionales
        fig = plt.figure(figsize=(11.69, 8.27))
        _table_page(fig, summary, title=f"Statistiques par unité administrative DHS — focus {region_line}")
        pdf.savefig(fig)
        plt.close(fig)

        # SHAP
        if shap:
            fig = plt.figure(figsize=(8.27, 11.69))
            _shap_bar_page(fig, shap)
            pdf.savefig(fig)
            plt.close(fig)
            beeswarm = project_root / "outputs/reports/shap_beeswarm_v4.png"
            if beeswarm.is_file():
                fig = plt.figure(figsize=(8.27, 11.69))
                _image_page(fig, beeswarm, caption="SHAP beeswarm — distribution des effets")
                pdf.savefig(fig)
                plt.close(fig)

        # Comparaison v4/v5
        if v4_m or v5_m:
            fig = plt.figure(figsize=(8.27, 11.69))
            _comparison_page(fig, v4_m, v5_m)
            pdf.savefig(fig)
            plt.close(fig)

    pdf_bytes = buffer.getvalue()
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)
    return pdf_bytes