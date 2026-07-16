"""
Démo Streamlit — Cameroon Poverty Mapping (Phase 3 ONG).

Usage:
  streamlit run streamlit_demo.py
  docker compose up streamlit
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import folium
import matplotlib.pyplot as plt
import pandas as pd
import rasterio
from rasterio.plot import show
import streamlit as st
import streamlit.components.v1 as components

from src.reports.ecam5_dashboard import build_ecam5_model_comparison
from src.reports.field_import import load_field_sites_for_report
from src.reports.pdf_report import generate_ngo_pdf_report
from src.reports.report_config import ReportOptions, load_report_config, t
from src.reports.region_stats import (
    DHS_REGIONS,
    REGION_BOUNDS,
    compute_regional_summary,
    filter_clusters_by_region,
    load_cluster_frame,
)
from src.reports.watchlist import evaluate_watchlist, format_alerts_text

PROJECT_ROOT = Path(__file__).resolve().parent

UI = {
    "fr": {
        "page_title": "Cameroon Poverty Mapping — ONG",
        "title": "Cameroon Poverty Mapping — Démo ONG",
        "caption": "Cartographie ~1 km · DHS 2018 · GEE · INS · Usage exploratoire uniquement",
        "filters": "Filtres & export",
        "admin_unit": "Unité administrative (DHS)",
        "raster_layer": "Couche raster",
        "layers": ["Richesse estimée", "Incertitude", "Actionnabilité", "Carte grappes"],
        "export": "Export",
        "pdf_btn": "Télécharger rapport PDF",
        "csv_btn": "Télécharger stats CSV",
        "clusters": "Grappes",
        "wealth_pred": "Wealth moyen (prédit)",
        "wealth_dhs": "Wealth moyen (DHS)",
        "uncertainty": "Incertitude moy.",
        "urban_rural": "Urbain / Rural",
        "map": "Carte",
        "side_panel": "Panneau latéral",
        "dynamic_stats": "Statistiques dynamiques",
        "shap": "SHAP — top variables",
        "shap_missing": "Exécutez `python scripts/compute_shap_v4.py` pour générer SHAP.",
        "ins_val": "Validation INS",
        "ins_missing": "Capture INS : `assets/screenshots/ins_validation_scatter_v4.png`",
        "tab_models": "Comparaison modèles",
        "tab_ecam5": "ECAM 5 vs modèle",
        "tab_regions": "Toutes les régions",
        "tab_field": "Validation terrain",
        "tab_about": "À propos",
        "alerts": "Alertes régionales",
        "no_alerts": "Aucune alerte pour les seuils configurés.",
        "field_upload": "Importer CSV terrain (optionnel)",
        "field_help": "Colonnes : site_id, region, lat, lon, local_assessment, …",
        "lang": "Langue",
        "about_md": """
        ### Phase 3 — Outils ONG
        - **Rapport PDF** configurable (FR/EN, sections, logo)
        - **ECAM 5** vs prédictions modèle par région
        - **Alertes** seuils régionaux (watchlist)
        - **Validation terrain** : import CSV partenaires

        **Éthique** : ne pas utiliser pour ciblage ménage/village ni remplacer l'INS.
        """,
        "run_hint": "Lancer : `streamlit run streamlit_demo.py`",
        "wealth_raster": "Indice de richesse estimé (v4)",
        "uncertainty_raster": "Incertitude du modèle",
        "priority_raster": "Indice d'actionnabilité / priorisation",
        "missing_file": "Fichier introuvable",
    },
    "en": {
        "page_title": "Cameroon Poverty Mapping — NGO",
        "title": "Cameroon Poverty Mapping — NGO Demo",
        "caption": "~1 km mapping · DHS 2018 · GEE · INS · Exploratory use only",
        "filters": "Filters & export",
        "admin_unit": "Administrative unit (DHS)",
        "raster_layer": "Raster layer",
        "layers": ["Estimated wealth", "Uncertainty", "Actionability", "Cluster map"],
        "export": "Export",
        "pdf_btn": "Download PDF report",
        "csv_btn": "Download stats CSV",
        "clusters": "Clusters",
        "wealth_pred": "Mean wealth (predicted)",
        "wealth_dhs": "Mean wealth (DHS)",
        "uncertainty": "Mean uncertainty",
        "urban_rural": "Urban / Rural",
        "map": "Map",
        "side_panel": "Side panel",
        "dynamic_stats": "Dynamic statistics",
        "shap": "SHAP — top features",
        "shap_missing": "Run `python scripts/compute_shap_v4.py` to generate SHAP.",
        "ins_val": "INS validation",
        "ins_missing": "INS screenshot: `assets/screenshots/ins_validation_scatter_v4.png`",
        "tab_models": "Model comparison",
        "tab_ecam5": "ECAM 5 vs model",
        "tab_regions": "All regions",
        "tab_field": "Field validation",
        "tab_about": "About",
        "alerts": "Regional alerts",
        "no_alerts": "No alerts for configured thresholds.",
        "field_upload": "Upload field CSV (optional)",
        "field_help": "Columns: site_id, region, lat, lon, local_assessment, …",
        "lang": "Language",
        "about_md": """
        ### Phase 3 — NGO tools
        - **Configurable PDF** report (FR/EN, sections, logo)
        - **ECAM 5** vs model predictions by region
        - **Threshold alerts** (watchlist)
        - **Field validation** : partner CSV import

        **Ethics** : not for household/village targeting; does not replace INS.
        """,
        "run_hint": "Run: `streamlit run streamlit_demo.py`",
        "wealth_raster": "Estimated wealth index (v4)",
        "uncertainty_raster": "Model uncertainty",
        "priority_raster": "Actionability / prioritization index",
        "missing_file": "File not found",
    },
}

MAP_PATH = PROJECT_ROOT / "outputs/maps/wealth_index_predicted_1km_model_v4.tif"
UNCERTAINTY_PATH = PROJECT_ROOT / "outputs/maps/wealth_uncertainty_1km_model_v4.tif"
PRIORITY_PATH = PROJECT_ROOT / "outputs/maps/priority_index_1km_actionable.tif"
FALLBACK_PRIORITY = PROJECT_ROOT / "outputs/maps/priority_index_1km_v4.tif"
INS_SCATTER = PROJECT_ROOT / "assets/screenshots/ins_validation_scatter_v4.png"
SHAP_JSON = PROJECT_ROOT / "site/assets/shap_summary.json"


@st.cache_data
def _load_clusters() -> pd.DataFrame:
    return load_cluster_frame(PROJECT_ROOT)


@st.cache_data
def _load_shap() -> dict:
    for p in (
        PROJECT_ROOT / "outputs/reports/shap_summary_v4.json",
        SHAP_JSON,
    ):
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def _load_ecam5_table() -> pd.DataFrame:
    try:
        return build_ecam5_model_comparison(PROJECT_ROOT)
    except Exception:
        return pd.DataFrame()


def _wealth_color(value: float, vmin: float, vmax: float) -> str:
    t_val = (value - vmin) / (vmax - vmin + 1e-9)
    r = int(220 * (1 - t_val) + 40 * t_val)
    g = int(60 * (1 - t_val) + 180 * t_val)
    b = int(60 * (1 - t_val) + 80 * t_val)
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_cluster_map(df: pd.DataFrame, region: str) -> folium.Map:
    if region != "Tout le Cameroun" and region in REGION_BOUNDS:
        (lat_lo, lon_lo), (lat_hi, lon_hi) = REGION_BOUNDS[region]
        center = [(lat_lo + lat_hi) / 2, (lon_lo + lon_hi) / 2]
        zoom = 8 if region in ("Douala", "Yaoundé") else 7
    else:
        center = [5.5, 12.5]
        zoom = 6

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")
    if df.empty:
        return m

    vmin = float(df["predicted_wealth"].min())
    vmax = float(df["predicted_wealth"].max())
    for row in df.itertuples(index=False):
        folium.CircleMarker(
            location=[row.latitude, row.longitude],
            radius=5,
            color="#333",
            weight=0.5,
            fill=True,
            fill_color=_wealth_color(float(row.predicted_wealth), vmin, vmax),
            fill_opacity=0.85,
            popup=(
                f"<b>{row.region}</b><br>"
                f"Cluster {row.cluster_id}<br>"
                f"Wealth prédit: {row.predicted_wealth:.0f}<br>"
                f"DHS: {row.wealth_index:.0f}<br>"
                f"Incertitude: {row.uncertainty_width:.0f}"
            ),
        ).add_to(m)
    return m


def _show_raster(path: Path, title: str, *, missing: str, cmap: str = "viridis") -> None:
    if not path.is_file():
        st.warning(f"{missing} : `{path}`")
        return
    with rasterio.open(path) as src:
        fig, ax = plt.subplots(figsize=(10, 7))
        show(src, ax=ax, title=title, cmap=cmap)
        st.pyplot(fig)
        plt.close(fig)


def _build_report_options(
    base: ReportOptions,
    *,
    lang: str,
    region: str,
    field_path: Path | None,
) -> ReportOptions:
    return ReportOptions(
        language=lang,
        region=region,
        organization=base.organization,
        logo_path=base.logo_path,
        contact_email=base.contact_email,
        sections=base.sections,
        field_csv=field_path or base.field_csv,
        watchlist_rules=base.watchlist_rules,
    )


# --- Config & language (before set_page_config uses lang) ---
_base_opts = load_report_config(project_root=PROJECT_ROOT)
if "lang" not in st.session_state:
    st.session_state.lang = _base_opts.language if _base_opts.language in ("fr", "en") else "fr"

st.set_page_config(
    page_title=UI[st.session_state.lang]["page_title"],
    layout="wide",
    initial_sidebar_state="expanded",
)

lang = st.session_state.lang
L = UI[lang]

# --- Header ---
st.title(L["title"])
st.caption(L["caption"])

# --- Sidebar ---
st.sidebar.header(L["filters"])
lang = st.sidebar.selectbox(
    L["lang"],
    ["fr", "en"],
    index=0 if st.session_state.lang == "fr" else 1,
    format_func=lambda x: "Français" if x == "fr" else "English",
)
st.session_state.lang = lang
L = UI[lang]

region = st.sidebar.selectbox(L["admin_unit"], DHS_REGIONS, index=0)
layer = st.sidebar.radio(L["raster_layer"], L["layers"], index=0)

uploaded = st.sidebar.file_uploader(L["field_upload"], type=["csv"], help=L["field_help"])
field_path: Path | None = None
if uploaded is not None:
    tmp = Path(tempfile.gettempdir()) / f"ngo_field_{uploaded.name}"
    tmp.write_bytes(uploaded.getvalue())
    field_path = tmp
else:
    field_path = _base_opts.field_csv

clusters = _load_clusters()
filtered = filter_clusters_by_region(clusters, region)
summary = compute_regional_summary(clusters, region=region)
full_summary = compute_regional_summary(clusters)
alerts = evaluate_watchlist(full_summary, _base_opts.watchlist_rules, lang=lang)

opts = _build_report_options(_base_opts, lang=lang, region=region, field_path=field_path)

st.sidebar.markdown("---")
st.sidebar.subheader(L["export"])
pdf_bytes = generate_ngo_pdf_report(PROJECT_ROOT, region=region, options=opts)
st.sidebar.download_button(
    label=L["pdf_btn"],
    data=pdf_bytes,
    file_name=f"ngo_report_{region.replace(' ', '_').lower()}_{lang}.pdf",
    mime="application/pdf",
)
csv_bytes = summary.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    label=L["csv_btn"],
    data=csv_bytes,
    file_name=f"stats_{region.replace(' ', '_').lower()}.csv",
    mime="text/csv",
)

# --- Alerts banner ---
st.sidebar.markdown("---")
st.sidebar.subheader(L["alerts"])
if alerts.empty:
    st.sidebar.success(L["no_alerts"])
else:
    for line in format_alerts_text(alerts, lang=lang)[1:]:
        st.sidebar.warning(line)

# --- Metrics row ---
if not summary.empty:
    row = summary.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(L["clusters"], int(row["n_clusters"]))
    c2.metric(L["wealth_pred"], f"{row['wealth_mean']:,.0f}")
    c3.metric(L["wealth_dhs"], f"{row['dhs_wealth_mean']:,.0f}")
    c4.metric(L["uncertainty"], f"{row['uncertainty_mean']:,.0f}")
    c5.metric(L["urban_rural"], f"{int(row['n_urban'])} / {int(row['n_rural'])}")

# --- Main layout ---
col_map, col_panel = st.columns([2, 1])

with col_map:
    st.subheader(f"{L['map']} — {region}")
    if layer == L["layers"][3]:
        m = _build_cluster_map(filtered, region)
        components.html(m.get_root().render(), height=520, scrolling=False)
    elif layer == L["layers"][0]:
        _show_raster(MAP_PATH, L["wealth_raster"], missing=L["missing_file"])
    elif layer == L["layers"][1]:
        _show_raster(UNCERTAINTY_PATH, L["uncertainty_raster"], missing=L["missing_file"], cmap="plasma")
    else:
        prio = PRIORITY_PATH if PRIORITY_PATH.is_file() else FALLBACK_PRIORITY
        _show_raster(prio, L["priority_raster"], missing=L["missing_file"], cmap="YlOrRd")

with col_panel:
    st.subheader(L["side_panel"])
    st.markdown(f"**{L['dynamic_stats']}**")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown(f"**{L['shap']}**")
    shap = _load_shap()
    items = shap.get("top10_mean_abs_shap", [])[:8]
    if items:
        shap_df = pd.DataFrame(
            [{"Variable": x["feature"], "Importance": x["mean_abs_shap"]} for x in items]
        )
        st.bar_chart(shap_df.set_index("Variable"))
    else:
        st.info(L["shap_missing"])

    st.markdown(f"**{L['ins_val']}**")
    if INS_SCATTER.is_file():
        cap = "Wealth prédit vs pauvreté INS (ECAM 4)" if lang == "fr" else "Predicted wealth vs INS poverty (ECAM 4)"
        st.image(str(INS_SCATTER), caption=cap)
    else:
        st.info(L["ins_missing"])

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [L["tab_models"], L["tab_ecam5"], L["tab_regions"], L["tab_field"], L["tab_about"]]
)

with tab1:
    v4_path = PROJECT_ROOT / "outputs/reports/model_v4_results.json"
    v5_path = PROJECT_ROOT / "outputs/reports/post_v1_action3_model_v5.json"
    cols = st.columns(2)
    if v4_path.is_file():
        v4 = json.loads(v4_path.read_text(encoding="utf-8")).get("metrics_v4_oof", {})
        cols[0].markdown("### Modèle v4" if lang == "fr" else "### Model v4")
        cols[0].write(v4)
    if v5_path.is_file():
        v5 = json.loads(v5_path.read_text(encoding="utf-8")).get("metrics_v5_post_oof", {})
        cols[1].markdown("### Modèle v5_post" if lang == "fr" else "### Model v5_post")
        cols[1].write(v5)

with tab2:
    ecam5 = _load_ecam5_table()
    if ecam5.empty:
        st.info("ECAM 5 data unavailable." if lang == "en" else "Données ECAM 5 indisponibles.")
    else:
        st.markdown(f"**{t('ecam5_title', lang)}**")
        st.dataframe(ecam5, use_container_width=True, hide_index=True)
        if "poverty_rate_pct" in ecam5.columns and "mean_predicted_wealth" in ecam5.columns:
            chart = ecam5.set_index("region")[["poverty_rate_pct", "mean_predicted_wealth"]]
            st.bar_chart(chart)

with tab3:
    st.dataframe(full_summary, use_container_width=True, hide_index=True)
    if not alerts.empty:
        st.markdown(f"**{t('watchlist_title', lang)}**")
        st.dataframe(alerts, use_container_width=True, hide_index=True)

with tab4:
    if field_path and field_path.is_file():
        try:
            field_df = load_field_sites_for_report(field_path)
            st.markdown(f"**{t('field_title', lang)}**")
            st.dataframe(field_df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(str(exc))
    else:
        st.info(
            "Importez un CSV ou configurez `field_validation.default_csv` dans configs/ngo_report.yaml."
            if lang == "fr"
            else "Upload a CSV or set `field_validation.default_csv` in configs/ngo_report.yaml."
        )

with tab5:
    map_url = "https://adamouabakar.github.io/cameroon-poverty-mapping/"
    gh_url = "https://github.com/adamouabakar/cameroon-poverty-mapping"
    st.markdown(L["about_md"])
    st.markdown(
        f"**Liens** : [Carte web]({map_url}) · [GitHub]({gh_url})"
        if lang == "fr"
        else f"**Links** : [Web map]({map_url}) · [GitHub]({gh_url})"
    )

st.sidebar.info(L["run_hint"])