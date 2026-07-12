# Cameroon Poverty Mapping

**Cartographie de la pauvreté au Cameroun à haute résolution (~1 km)**  
Combinaison de données DHS 2018, Google Earth Engine et validation avec les statistiques officielles de l’INS.

![GitHub Release](https://img.shields.io/github/v/release/adamouabakar/cameroon-poverty-mapping?style=flat-square)
![License](https://img.shields.io/github/license/adamouabakar/cameroon-poverty-mapping?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![GEE](https://img.shields.io/badge/Google_Earth_Engine-Enabled-green?style=flat-square)
![Stars](https://img.shields.io/github/stars/adamouabakar/cameroon-poverty-mapping?style=flat-square)

## 🎯 Objectif

Produire une **cartographie fine, rigoureuse et actionnable** de la pauvreté au Cameroun en combinant :
- Enquêtes terrain (DHS 2018)
- Données satellitaires (Sentinel-2, VIIRS, GHSL, CHIRPS)
- **Validation externe** avec les données officielles de l’**Institut National de la Statistique (INS)**

## ✨ Résultats Principaux (v2.0.0)

- **430 grappes DHS réelles** traitées
- **Modèle v5_post** (GEE v3 + INS ECAM 5 + accessibilité)
- **Performance du modèle** :
  - R² OOF : **0.809**
  - Spearman : **0.899**
- Cartes nationales avec **incertitude** et **zones d’actionnabilité**
- Validation externe avec données INS (cohérence régionale forte)

## 📊 Visualisations & Cartes

### Carte Nationale de Pauvreté Estimée
![Pauvreté Estimée](outputs/maps/wealth_index_predicted_1km_model_v4.png)

### Carte d’Incertitude
![Incertitude](outputs/maps/wealth_uncertainty_1km_model_v4.png)

### Carte d’Actionnabilité (Zones Prioritaires)
![Actionnabilité](outputs/maps/priority_index_1km_v4.png)

### Validation Externe avec Données INS
![Validation INS](outputs/maps/ins_external_validation_scatter.png)

## 🚀 Comment Reproduire le Projet

```bash
git clone https://github.com/adamouabakar/cameroon-poverty-mapping.git
cd cameroon-poverty-mapping

# Installation des dépendances
pip install -r requirements.txt

# Exécution complète du pipeline
python scripts/run_pipeline.py