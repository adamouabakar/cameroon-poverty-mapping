import streamlit as st
import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Cameroon Poverty Mapping", layout="wide")
st.title("🗺️ Cameroon Poverty Mapping - v1.1.0")
st.markdown("**Cartographie de la pauvreté à ~1 km** | Validation INS + Incertitude + SHAP")

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choisir une vue", 
    ["Carte Principale", "Incertitude", "Actionnabilité", "Validation INS", "À propos"])

# Chemins (adapte si nécessaire)
MAP_PATH = Path("outputs/maps/wealth_index_predicted_1km_model_v4.tif")
UNCERTAINTY_PATH = Path("outputs/maps/wealth_uncertainty_1km_model_v4.tif")
PRIORITY_PATH = Path("outputs/maps/priority_index_1km_v4.tif")

if page == "Carte Principale":
    st.subheader("Pauvreté Estimée (v4)")
    if MAP_PATH.exists():
        with rasterio.open(MAP_PATH) as src:
            fig, ax = plt.subplots(figsize=(12, 8))
            show(src, ax=ax, title="Indice de Richesse Estimé")
            st.pyplot(fig)
    else:
        st.warning("Carte principale non trouvée. Exécute le pipeline d'abord.")

elif page == "Incertitude":
    st.subheader("Carte d'Incertitude")
    if UNCERTAINTY_PATH.exists():
        with rasterio.open(UNCERTAINTY_PATH) as src:
            fig, ax = plt.subplots(figsize=(12, 8))
            show(src, ax=ax, title="Incertitude du Modèle", cmap="viridis")
            st.pyplot(fig)
    else:
        st.warning("Carte d'incertitude non trouvée.")

elif page == "Actionnabilité":
    st.subheader("Zones d'Actionnabilité")
    if PRIORITY_PATH.exists():
        with rasterio.open(PRIORITY_PATH) as src:
            fig, ax = plt.subplots(figsize=(12, 8))
            show(src, ax=ax, title="Priorité d'Intervention")
            st.pyplot(fig)
    else:
        st.warning("Carte d'actionnabilité non trouvée.")

elif page == "Validation INS":
    st.subheader("Validation Externe avec Données INS")
    st.markdown("Spearman : **-0.87** | Bonne cohérence régionale observée.")
    st.image("outputs/maps/ins_external_validation_scatter.png", use_column_width=True)

elif page == "À propos":
    st.markdown("""
    ### À propos du projet
    - **Auteur** : Abubakr Adamou (@Adamou_Aboubakr)
    - **Version** : v1.1.0
    - **Données** : DHS 2018 + GEE + Validation INS
    - **Objectif** : Aider les ONG et décideurs à mieux cibler les interventions
    """)

st.sidebar.info("Pour exécuter localement : `streamlit run streamlit_demo.py`")