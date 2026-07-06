# Méthodologie

Cette section décrit le pipeline méthodologique du projet de cartographie fine de la pauvreté au Cameroun. L’approche repose sur un apprentissage supervisé ancré sur les grappes DHS, une extraction de features géospatiales ouvertes à l’échelle nationale, et une phase exploratoire de priorisation spatiale. Chaque choix méthodologique est explicité, ainsi que ses limites et ses implications pour l’interprétation des résultats.

## 1. Sources de données

### 1.1 Enquête DHS Cameroun 2018

**Statut (juillet 2026) :** intégration réelle terminée — **430 grappes**, sortie `data/processed/dhs_clusters_real.parquet`.

La variable cible provient de l’**Enquête Démographique et de Santé (DHS) Cameroun 2018** (ICF, 2019). Pour chaque grappe, nous utilisons :
- l’**indice de richesse** (*Wealth Index*), calculé par analyse en composantes principales à partir des actifs du ménage ;
- les **coordonnées GPS** des grappes (avec jitter) ;
- les variables de stratification (urbain/rural, région) pour les analyses de performance.

Les microdonnées DHS ne sont pas redistribuées dans ce dépôt. Leur accès nécessite une demande auprès du [programme DHS](https://dhsprogram.com/).

### 1.2 Jitter GPS et implications méthodologiques
Les coordonnées des grappes DHS sont **délibérément déplacées** pour protéger la confidentialité des répondants :

| Contexte          | Déplacement maximal |
|-------------------|---------------------|
| Zones urbaines    | 2 km                |
| Zones rurales     | 5 km                |
| ~1 % des grappes  | jusqu’à 10 km       |

Ce jitter impose plusieurs contraintes méthodologiques :
- La résolution effective du modèle est limitée par l’incertitude de localisation.
- Les features sont agrégées sur des **buffers** autour de chaque grappe (minimum 2 km en urbain, 5 km en rural).
- Une validation naïve sur les coordonnées exactes peut biaiser les métriques.
- Les cartes produites sont des **estimations écologiques** (au niveau de la zone), et non des prédictions au niveau individuel ou du ménage.

### 1.3 Données satellitaires et géospatiales ouvertes
L’ensemble des prédicteurs provient exclusivement de sources ouvertes :

| Source          | Variables principales                     | Résolution |
|-----------------|-------------------------------------------|------------|
| Sentinel-2      | Bandes spectrales, NDVI, NDBI, NDWI       | 10–20 m    |
| VIIRS           | Luminosité nocturne                       | ~500 m     |
| OpenStreetMap   | Distances aux routes, bâtiments, services | Vectoriel  |
| WorldPop        | Densité de population                     | 100 m      |
| SRTM            | Élévation, pente                          | 30 m       |

### 1.4 Architecture technique
Le pipeline utilise une architecture **hybride** :
- **Google Earth Engine (GEE)** pour l’extraction des features à grande échelle.
- **Environnement local** pour l’entraînement, la validation et la production finale des cartes.

Cette séparation permet d’exécuter le pipeline sans infrastructure lourde.

## 2. Proxy de pauvreté

La **variable cible** est l’indice de richesse DHS au niveau de la grappe. Ce choix est motivé par :
- Sa disponibilité harmonisée et documentée.
- Sa forte corrélation avec le niveau de vie des ménages.
- Son utilisation standard dans la littérature (Jean et al., 2016 ; Yeh et al., 2020).

**Limite importante** : l’indice de richesse est un **proxy** du bien-être économique. Il ne mesure pas directement la consommation, le revenu ni la pauvreté multidimensionnelle.

## 3. Architecture du modèle

### 3.1 Modèle principal (hybride)
Le modèle principal combine :
- Des **features tabulaires** riches extraites à la résolution cible.
- Un modèle de **gradient boosting** (LightGBM par défaut).

Cette approche offre un bon équilibre entre performance, interprétabilité et coût computationnel, particulièrement adapté au nombre relativement limité de grappes DHS au Cameroun.

### 3.2 Option exploratoire (CNN)
Une approche secondaire basée sur le fine-tuning d’un petit CNN (EfficientNet ou MobileNet) est proposée à titre comparatif. Elle reste optionnelle en raison de son coût plus élevé et du risque de surapprentissage avec un nombre limité de grappes.

## 4. Stratégie d’entraînement et de validation

### 4.1 Validation croisée spatiale
Pour éviter le *spatial leakage*, nous utilisons une **validation croisée spatiale** (cluster-based ou block-based). Les grappes de validation sont géographiquement séparées de celles utilisées pour l’entraînement.

### 4.2 Métriques

Les performances sont évaluées avec :
- R², RMSE, MAE
- Corrélation de Spearman
- Analyses stratifiées (urbain/rural, régions)

**Résultats OOF sur données réelles (v3, 430 grappes, block CV) :**

| Métrique | Valeur |
|----------|--------|
| R² | 0.776 |
| Spearman | 0.875 |
| RMSE | 39 939 |
| MAE | 30 660 |

Rapport détaillé : `outputs/reports/real_model_results.json`

### 4.3 Gestion du jitter
Outre l’agrégation par buffer, des analyses de sensibilité sont réalisées avec différents rayons de buffer et différentes méthodes de modélisation de l’erreur de localisation.

## 5. Extraction des features

Les features sont extraites principalement via **Google Earth Engine** à la résolution cible de **500 m à 1 km** (1 km par défaut pour la carte nationale). Les features incluent des informations spectrales, de texture, de luminosité nocturne, d’accessibilité (OSM) et démographiques (WorldPop).

Une voie d’extraction **locale** est également prévue pour les zones tests et le développement itératif.

## 6. Phase 2 — Priorisation spatiale

La Phase 2 transforme la carte de bien-être en un **indice composite de priorisation** en combinant :
- La pauvreté estimée (inverse de l’indice de richesse)
- L’accessibilité aux écoles, centres de santé et routes (via OpenStreetMap)

Cet indice est **exploratoire**. Il ne repose pas sur une relation causale et sert à identifier des zones où une intervention pourrait être explorée en priorité, sous réserve de validation locale.

## 7. Incertitude

Des **cartes d’incertitude** sont produites en agrégant les prédictions issues de la validation croisée spatiale (approche *ensemble*). Elles accompagnent systématiquement les cartes de bien-être et de priorisation.

## 8. Considérations pour une résolution plus fine

Le pipeline est conçu pour une résolution de référence de 500 m–1 km. Pour descendre sous 500 m sur des zones tests, plusieurs pistes sont envisagées (imagerie haute résolution, CNN, fusion multi-échelle), avec l’obligation d’accompagner toute carte fine d’un avertissement sur la limite imposée par le jitter DHS.

---

**Références méthodologiques** (déjà présentes dans ta version)

*(Tu peux garder les références que tu avais déjà listées à la fin de ta version.)*