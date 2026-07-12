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

Cartes nationales à **1 km** (modèle v4/v5_post, DHS 2018 + GEE + INS). Usage exploratoire — croiser toujours l’incertitude.

### Carte nationale — indice de richesse estimé

Proxy DHS au niveau pixel ; les zones sombres correspondent aux estimations de bien-être plus faible.

![Carte nationale de pauvreté estimée — résolution 1 km, modèle v4](assets/screenshots/poverty_map_national_v4.png)

### Carte d’incertitude du modèle

Variabilité des prédictions (ensemble CV spatial). Les zones à incertitude élevée demandent une validation locale avant toute lecture fine.

![Carte d’incertitude — modèle v4, 1 km](assets/screenshots/uncertainty_map_v4.png)

### Carte d’actionnabilité — priorisation exploratoire

Indice composite pauvreté estimée + accessibilité (écoles, santé, routes OSM). **Non opérationnel** — aide à prioriser des zones pour dialogue partenaire, pas pour allocation budgétaire.

![Carte d’actionnabilité — indice de priorisation, v4](assets/screenshots/actionability_map_v4.png)

### Validation externe — modèle vs INS (ECAM 4)

Concordance régionale entre prédictions OOF et taux de pauvreté monétaire INS ; Spearman ≈ **−0.87** (12 régions).

![Validation externe INS — wealth prédit vs pauvreté ECAM 4 par région](assets/screenshots/ins_validation_scatter_v4.png)

## 🚀 Comment Reproduire

```bash
git clone https://github.com/adamouabakar/cameroon-poverty-mapping.git
cd cameroon-poverty-mapping

pip install -r requirements.txt

# Pipeline complet
python scripts/run_pipeline.py