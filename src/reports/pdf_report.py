"""Générateur de rapport PDF professionnel pour ONG — Phase 3."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from src.reports.ecam5_dashboard import build_ecam5_model_comparison
from src.reports.field_import import load_field_sites_for_report
from src.reports.report_config import ReportOptions, load_report_config, t
from src.reports.region_stats import compute_regional_summary, load_cluster_frame
from src.reports.watchlist import evaluate_watchlist, format_alerts_text

DEFAULT_SCREENSHOTS = {
    "wealth": "assets/screenshots/poverty_map_national_v4.png",
    "uncertainty": "assets/screenshots/uncertainty_map_v4.png",
    "priority": "assets/screenshots/actionability_map_v4.png",
    "ins": "assets/screenshots/ins_validation_scatter_v4.png",
}

MAP_CAPTIONS = {
    "wealth": {
        "fr": "Carte nationale — indice de richesse estimé (1 km)",
        "en": "National map — estimated wealth index (1 km)",
    },
    "uncertainty": {
        "fr": "Carte d'incertitude du modèle",
        "en": "Model uncertainty map",
    },
    "priority": {
        "fr": "Carte d'actionnabilité / priorisation exploratoire",
        "en": "Actionability / prioritization map (exploratory)",
    },
    "ins": {
        "fr": "Validation externe — modèle vs pauvreté INS par région",
        "en": "External validation — model vs INS poverty by region",
    },
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


def _logo_page(fig: Figure, logo_path: Path) -> None:
    ax = fig.add_axes([0.25, 0.35, 0.5, 0.3])
    ax.axis("off")
    img = plt.imread(logo_path)
    ax.imshow(img)


def _image_page(fig: Figure, img_path: Path, *, caption: str) -> None:
    ax = fig.add_axes([0.05, 0.12, 0.9, 0.78])
    ax.axis("off")
    if img_path.is_file():
        ax.imshow(plt.imread(img_path))
    else:
        ax.text(0.5, 0.5, f"Missing:\n{img_path.name}", ha="center", va="center")
    fig.text(0.05, 0.04, caption, fontsize=9, style="italic")


def _table_page(fig: Figure, df: pd.DataFrame, *, title: str) -> None:
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=20)
    if df.empty:
        ax.text(0.05, 0.5, "—", fontsize=11)
        return
    show = df.head(16)
    table = ax.table(
        cellText=show.values,
        colLabels=show.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.3)


def _shap_bar_page(fig: Figure, shap_data: dict[str, Any], *, lang: str) -> None:
    ax = fig.add_axes([0.12, 0.15, 0.82, 0.7])
    items = shap_data.get("top10_mean_abs_shap", [])[:10]
    if not items:
        ax.text(0.5, 0.5, "SHAP N/A", ha="center")
        ax.axis("off")
        return
    labels = [x["feature"] for x in items][::-1]
    vals = [x["mean_abs_shap"] for x in items][::-1]
    ax.barh(labels, vals, color="#2c7bb6")
    ax.set_xlabel("|SHAP|")
    title = "SHAP feature importance" if lang == "en" else "Importance des variables (SHAP)"
    ax.set_title(title, fontweight="bold")


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
    ax.set_title("Model comparison (OOF)", fontweight="bold")


def _section_enabled(opts: ReportOptions, key: str) -> bool:
    return opts.sections.get(key, True)


def generate_ngo_pdf_report(
    project_root: Path,
    *,
    region: str = "Tout le Cameroun",
    output_path: Path | None = None,
    options: ReportOptions | None = None,
) -> bytes:
    """Génère un rapport PDF multi-pages configurable (Phase 3)."""
    project_root = Path(project_root)
    opts = options or load_report_config(project_root=project_root)
    opts.region = region
    lang = opts.language if opts.language in ("fr", "en") else "fr"

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
    region_line = region if region != "Tout le Cameroun" else t("national_view", lang)

    full_summary = compute_regional_summary(clusters)
    alerts = evaluate_watchlist(full_summary, opts.watchlist_rules, lang=lang)

    field_df = pd.DataFrame()
    field_path = opts.field_csv
    if field_path and field_path.is_file():
        try:
            field_df = load_field_sites_for_report(field_path)
        except Exception:
            field_df = pd.DataFrame()

    ecam5_df = pd.DataFrame()
    if _section_enabled(opts, "ecam5_comparison"):
        try:
            ecam5_df = build_ecam5_model_comparison(project_root)
        except Exception:
            ecam5_df = pd.DataFrame()

    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        if _section_enabled(opts, "cover"):
            fig = plt.figure(figsize=(8.27, 11.69))
            if opts.logo_path and opts.logo_path.is_file():
                _logo_page(fig, opts.logo_path)
            exec_label = "Résumé exécutif" if lang == "fr" else "Executive summary"
            ethics_label = "Avertissement" if lang == "fr" else "Ethics notice"
            lines = [
                f"{opts.organization}",
                f"Date : {now}",
                f"{'Périmètre' if lang == 'fr' else 'Scope'} : {region_line}",
                "",
                exec_label,
                f"• Model {metrics.get('model', 'v4')} — R² {metrics.get('r2', 0):.3f}, "
                f"Spearman {metrics.get('spearman', 0):.3f}",
                f"• DHS clusters : {len(clusters)}",
            ]
            if ins_spearman is not None:
                lines.append(f"• INS ECAM4 Spearman : {ins_spearman:.3f}")
            lines.extend(["", ethics_label, t("ethics", lang), "", opts.contact_email])
            _text_page(fig, lines, title=t("cover_title", lang))
            pdf.savefig(fig)
            plt.close(fig)

        if _section_enabled(opts, "maps"):
            for key in ("wealth", "uncertainty", "priority", "ins"):
                fig = plt.figure(figsize=(8.27, 11.69))
                _image_page(
                    fig,
                    project_root / DEFAULT_SCREENSHOTS[key],
                    caption=MAP_CAPTIONS[key][lang],
                )
                pdf.savefig(fig)
                plt.close(fig)

        if _section_enabled(opts, "regional_stats"):
            fig = plt.figure(figsize=(11.69, 8.27))
            _table_page(
                fig,
                summary,
                title=f"{t('regional_stats', lang)} — {region_line}",
            )
            pdf.savefig(fig)
            plt.close(fig)

        if _section_enabled(opts, "ecam5_comparison") and not ecam5_df.empty:
            cols = [
                "region", "n_clusters", "mean_predicted_wealth",
                "poverty_rate_pct", "rank_gap",
            ]
            fig = plt.figure(figsize=(11.69, 8.27))
            _table_page(fig, ecam5_df[cols], title=t("ecam5_title", lang))
            pdf.savefig(fig)
            plt.close(fig)

        if _section_enabled(opts, "watchlist_alerts"):
            fig = plt.figure(figsize=(8.27, 11.69))
            _text_page(fig, format_alerts_text(alerts, lang=lang), title="")
            pdf.savefig(fig)
            plt.close(fig)

        if _section_enabled(opts, "field_validation") and not field_df.empty:
            fig = plt.figure(figsize=(11.69, 8.27))
            _table_page(fig, field_df, title=t("field_title", lang))
            pdf.savefig(fig)
            plt.close(fig)

        if _section_enabled(opts, "shap") and shap:
            fig = plt.figure(figsize=(8.27, 11.69))
            _shap_bar_page(fig, shap, lang=lang)
            pdf.savefig(fig)
            plt.close(fig)
            beeswarm = project_root / "outputs/reports/shap_beeswarm_v4.png"
            if beeswarm.is_file():
                fig = plt.figure(figsize=(8.27, 11.69))
                cap = "SHAP beeswarm" if lang == "en" else "SHAP beeswarm — distribution"
                _image_page(fig, beeswarm, caption=cap)
                pdf.savefig(fig)
                plt.close(fig)

        if _section_enabled(opts, "model_comparison") and (v4_m or v5_m):
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