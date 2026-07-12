#!/usr/bin/env python
"""
Démo Streamlit — Cameroon Poverty Mapping (Phase 2 ONG).

Usage:
  streamlit run streamlit_demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

import folium
import matplotlib.pyplot as plt
import pandas as pd
import rasterio
from rasterio.plot import show
import streamlit as st
import streamlit.components.v1 as components

from src.reports.pdf_report import generate_ngo_pdf_report
from src.reports.region_stats import (
    DHS_REGIONS,
    REGION_BOUNDS,
    compute_regional_summary,
    filter_clusters_by_region,
    load_cluster_frame,
)

PROJECT_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Cameroon Poverty Mapping — ONG",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Paths ---
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


def _wealth_color(value: float, vmin: float, vmax: float) -> str:
    t = (value - vmin) / (vmax - vmin + 1e-9)
    r = int(220 * (1 - t) + 40 * t)
    g = int(60 * (1 - t) + 180 * t)
    b = int(60 * (1 - t) + 80 * t)
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


def _show_raster(path: Path, title: str, cmap: str = "viridis") -> None:
    if not path.is_file():
        st.warning(f"Fichier introuvable : `{path}`")
        return
    with rasterio.open(path) as src:
        fig, ax = plt.subplots(figsize=(10, 7))
        show(src, ax=ax, title=title, cmap=cmap)
        st.pyplot(fig)
        plt.close(fig)


# --- Header ---
st.title("Cameroon Poverty Mapping — Démo ONG")
st.caption("Cartographie ~1 km · DHS 2018 · GEE · INS · Usage exploratoire uniquement")

# --- Sidebar ---
st.sidebar.header("Filtres & export")
region = st.sidebar.selectbox("Unité administrative (DHS)", DHS_REGIONS, index=0)
layer = st.sidebar.radio(
    "Couche raster",
    ["Richesse estimée", "Incertitude", "Actionnabilité", "Carte grappes"],
    index=0,
)

clusters = _load_clusters()
filtered = filter_clusters_by_region(clusters, region)
summary = compute_regional_summary(clusters, region=region)

st.sidebar.markdown("---")
st.sidebar.subheader("Export")
pdf_bytes = generate_ngo_pdf_report(PROJECT_ROOT, region=region)
st.sidebar.download_button(
    label="Télécharger rapport PDF",
    data=pdf_bytes,
    file_name=f"ngo_report_{region.replace(' ', '_').lower()}.pdf",
    mime="application/pdf",
)
csv_bytes = summary.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    label="Télécharger stats CSV",
    data=csv_bytes,
    file_name=f"stats_{region.replace(' ', '_').lower()}.csv",
    mime="text/csv",
)

# --- Metrics row ---
if not summary.empty:
    row = summary.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Grappes", int(row["n_clusters"]))
    c2.metric("Wealth moyen (prédit)", f"{row['wealth_mean']:,.0f}")
    c3.metric("Wealth moyen (DHS)", f"{row['dhs_wealth_mean']:,.0f}")
    c4.metric("Incertitude moy.", f"{row['uncertainty_mean']:,.0f}")
    c5.metric("Urbain / Rural", f"{int(row['n_urban'])} / {int(row['n_rural'])}")

# --- Main layout ---
col_map, col_panel = st.columns([2, 1])

with col_map:
    st.subheader(f"Carte — {region}")
    if layer == "Carte grappes":
        m = _build_cluster_map(filtered, region)
        components.html(m.get_root().render(), height=520, scrolling=False)
    elif layer == "Richesse estimée":
        _show_raster(MAP_PATH, "Indice de richesse estimé (v4)")
    elif layer == "Incertitude":
        _show_raster(UNCERTAINTY_PATH, "Incertitude du modèle", cmap="plasma")
    else:
        prio = PRIORITY_PATH if PRIORITY_PATH.is_file() else FALLBACK_PRIORITY
        _show_raster(prio, "Indice d'actionnabilité / priorisation", cmap="YlOrRd")

with col_panel:
    st.subheader("Panneau latéral")
    st.markdown("**Statistiques dynamiques**")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown("**SHAP — top variables**")
    shap = _load_shap()
    items = shap.get("top10_mean_abs_shap", [])[:8]
    if items:
        shap_df = pd.DataFrame(
            [{"Variable": x["feature"], "Importance": x["mean_abs_shap"]} for x in items]
        )
        st.bar_chart(shap_df.set_index("Variable"))
    else:
        st.info("Exécutez `python scripts/compute_shap_v4.py` pour générer SHAP.")

    st.markdown("**Validation INS**")
    if INS_SCATTER.is_file():
        st.image(str(INS_SCATTER), caption="Wealth prédit vs pauvreté INS (ECAM 4)")
    else:
        st.info("Capture INS : `assets/screenshots/ins_validation_scatter_v4.png`")

# --- Tabs bas de page ---
tab1, tab2, tab3 = st.tabs(["Comparaison modèles", "Toutes les régions", "À propos"])

with tab1:
    v4_path = PROJECT_ROOT / "outputs/reports/model_v4_results.json"
    v5_path = PROJECT_ROOT / "outputs/reports/post_v1_action3_model_v5.json"
    cols = st.columns(2)
    if v4_path.is_file():
        v4 = json.loads(v4_path.read_text(encoding="utf-8")).get("metrics_v4_oof", {})
        cols[0].markdown("### Modèle v4")
        cols[0].write(v4)
    if v5_path.is_file():
        v5 = json.loads(v5_path.read_text(encoding="utf-8")).get("metrics_v5_post_oof", {})
        cols[1].markdown("### Modèle v5_post")
        cols[1].write(v5)

with tab2:
    full = compute_regional_summary(clusters)
    st.dataframe(full, use_container_width=True, hide_index=True)

with tab3:
    st.markdown(
        """
        ### Phase 2 — Outils ONG
        - **Rapport PDF** : cartes, stats régionales, SHAP, comparaison v4/v5
        - **Sélecteur administratif** : 12 régions DHS + vue nationale
        - **Export** : PDF et CSV depuis la barre latérale

        **Éthique** : ne pas utiliser pour ciblage ménage/village ni remplacer l'INS.

        **Liens** : [Carte web](https://adamouabakar.github.io/cameroon-poverty-mapping/) ·
        [GitHub](https://github.com/adamouabakar/cameroon-poverty-mapping)
        """
    )

st.sidebar.info("Lancer : `streamlit run streamlit_demo.py`")