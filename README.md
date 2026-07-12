# Cameroon Poverty Mapping

**Cartographie de la pauvreté au Cameroun à haute résolution (~1 km)**  
Combinaison de données DHS 2018, Google Earth Engine et validation avec les statistiques officielles de l’INS.

![GitHub Release](https://img.shields.io/github/v/release/adamouabakar/cameroon-poverty-mapping?style=flat-square)
![License](https://img.shields.io/github/license/adamouabakar/cameroon-poverty-mapping?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)
![GEE](https://img.shields.io/badge/Google_Earth_Engine-Enabled-green?style=flat-square)

## 🎯 Pourquoi ce projet ?

À 20 ans, en partant de données limitées et de ressources modestes au Cameroun, ce projet vise à produire une **cartographie fine et actionnable** de la pauvreté pour aider les chercheurs, les ONG et les décideurs à mieux cibler les interventions.

## ✨ Résultats Principaux (v1.1.0)

- **430 grappes DHS 2018** réelles traitées
- **Feature Set v4** avec variables contextuelles INS
- **Performance du modèle** :
  - R² OOF : **0.793**
  - Spearman : **0.889**
- Cartes nationales avec **incertitude** et **zones d’actionnabilité**
- Validation externe avec données officielles INS (cohérence régionale forte)

## 📊 Visualisations & Cartes

### Carte Nationale de Pauvreté Estimée (v4)
![Pauvreté Estimée](outputs/maps/wealth_index_predicted_1km_model_v4.png)

### Carte d’Incertitude
![Incertitude](outputs/maps/wealth_uncertainty_1km_model_v4.png)

### Carte d’Actionnabilité (Zones Prioritaires)
![Actionnabilité](outputs/maps/priority_index_1km_v4.png)

### Validation Externe avec Données INS
![Validation INS](outputs/maps/ins_external_validation_scatter.png)

## 🚀 Comment Reproduire

```bash
git clone https://github.com/adamouabakar/cameroon-poverty-mapping.git
cd cameroon-poverty-mapping

pip install -r requirements.txt

# Pipeline complet
python scripts/run_pipeline.py