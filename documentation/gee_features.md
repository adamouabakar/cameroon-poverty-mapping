# Extraction de features Google Earth Engine

Documentation du pipeline GEE — **validé sur 430 grappes DHS réelles (juillet 2026)**, feature set **v3** (GHSL + CHIRPS).

---

## Objectif

Remplacer les 10 features fictives du Notebook 02 par des variables géospatiales réelles extraites via Google Earth Engine, **sans modifier les noms de colonnes** du modèle.

**Sortie principale :** `data/processed/features/cluster_features_gee.parquet`  
**Projet GEE :** `cameroon-poverty-mapping` (`configs/gee.yaml`)

---

## Les 10 features finales

| Colonne modèle | Bande GEE interne | Description | Unité attendue |
|----------------|-------------------|-------------|----------------|
| `night_lights_mean` | `night_lights` | Luminosité nocturne VIIRS (médiane 2018, masque qualité) | radiance (sans unité normalisée) |
| `ndvi_mean` | `ndvi` | Indice de végétation (Sentinel-2, médiane 2017–2019) | [-1, 1] |
| `ndbi_mean` | `ndbi` | Indice zones bâties / surfaces imperméables (S2 dérivé) | [-1, 1] |
| `dist_road_km` | `dist_road_m` → /1000 | Distance moyenne à la route la plus proche | km |
| `dist_school_km` | `dist_school_m` → /1000 | Distance moyenne à l'établissement scolaire le plus proche | km |
| `dist_health_km` | `dist_health_m` → /1000 | Distance moyenne au centre de santé le plus proche | km |
| `pop_density` | `pop_density` | Population WorldPop (moyenne buffer) | pers/pixel 1 km (densité relative) |
| `elevation_m` | `elevation` | Élévation SRTM | m |
| `slope_deg` | `slope` | Pente terrain (SRTM) | degrés |
| `built_density` | `built_density` | Fraction de surface bâtie (WorldCover classe 50) | [0, 1] |

Bandes QA internes (non exportées vers le modèle) : `ndwi`, `evi`.

### Jeux de features (`feature_set`)

| Version | Bâti | Précipitations | Nb colonnes |
|---------|------|----------------|-------------|
| **v1** | `built_density` (WorldCover 2021) | — | 10 |
| **v2** | `ghsl_built_fraction` (GHSL 2015) | — | 10 |
| **v3** | `ghsl_built_fraction` (GHSL 2015) | CHIRPS 2018 | 13 |

Activer via `feature_set` dans `configs/gee.yaml` (défaut : **v2**). Le stack ajoute CHIRPS uniquement si les colonnes precip sont présentes dans `feature_columns`.

### Features CHIRPS (v3 uniquement)

| Colonne modèle | Bande GEE interne | Description | Unité |
|----------------|-------------------|-------------|-------|
| `precip_annual_mm` | `precip_annual` | Somme des précipitations journalières sur 2018 | mm |
| `precip_wet_season_mm` | `precip_wet` | Somme mars–novembre (saison humide, hémisphère nord) | mm |
| `precip_cv` | `precip_cv` | Coefficient de variation intra-annuel (σ / μ des jours) | sans unité |

**Dataset :** `UCSB-CHG/CHIRPS/DAILY` — résolution native ~5,5 km, reprojeté à 1 km (`export_scale`).  
**Module :** `src/features/gee/composites/chirps.py`  
**Config :** section `chirps` dans `configs/gee.yaml` (`start`/`end`, `wet_season_start_month`/`wet_season_end_month`).

---

## Datasets GEE et sources auxiliaires

### Imagery et dérivés (GEE natif)

| Feature(s) | ID collection / image GEE | Période | Composite / traitement | Reducer buffer |
|------------|---------------------------|---------|------------------------|----------------|
| `ndvi_mean`, `ndbi_mean` | `COPERNICUS/S2_SR_HARMONIZED` | 2017-01-01 → 2019-12-31 | Filtre nuages <20 %, masque QA60, médiane, réflectance /10000, indices | **mean** |
| `night_lights_mean` | `NASA/VIIRS/002/VNP46A2` | 2018 | Masque `Mandatory_Quality_Flag ∈ {0,1}`, médiane ; bande `Gap_Filled_DNB_BRDF_Corrected_NTL` | **mean** |
| `elevation_m` | `USGS/SRTMGL1_003` | statique | Bande `elevation` | **mean** |
| `slope_deg` | `USGS/SRTMGL1_003` | statique | `ee.Terrain.slope` | **mean** |
| `pop_density` | `WorldPop/GP/100m/pop` | 2018 | `mosaic()` année 2018, `unmask(0)` | **mean** |
| `built_density` | `ESA/WorldCover/v200` | 2021 (image unique) | Classe 50 (built-up) → masque binaire | **mean** |
| `ghsl_built_fraction` | `JRC/GHSL/P2023A/GHS_BUILT_S` | 2015 | `built_surface` (m²) → fraction [0, 1] | **mean** |
| `precip_annual_mm`, `precip_wet_season_mm`, `precip_cv` | `UCSB-CHG/CHIRPS/DAILY` | 2018 | Somme annuelle, somme saison humide (M3–M11), CV journalier | **mean** |

### Infrastructures (FeatureCollections)

| Feature | Source | Asset / fichier | Notes |
|---------|--------|-----------------|-------|
| `dist_road_km` | GRIP4 | `projects/sat-io/open-datasets/GRIP4/Africa` | Routes globales ; `fastDistanceTransform` @ 1 km |
| `dist_health_km` | Global Healthsites | `health-site-node` + `health-site-way` | Filtre `healthcare` / `amenity` |
| `dist_school_km` | **HOT/OSM Cameroun (HDX)** | `data/processed/hotosm_cmr_education_points.geojson` | **10 186 points** ; pas d'asset GEE public trouvé |

> **Écoles :** jeu [HOT `hotosm_cmr_education_facilities`](https://data.humdata.org/dataset/hotosm_cmr_education_facilities) (OSM, juin 2026), préparé par `scripts/prepare_hotosm_schools.py`, chargé côté client en `ee.FeatureCollection`.

### Justifications temporelles

- **Sentinel-2 2017–2019** : fenêtre ±1 an autour de la collecte DHS 2018 ; médiane robuste aux nuages.
- **VIIRS 2018** : année d'enquête.
- **WorldPop 2018** : aligné DHS.
- **WorldCover 2021** : décalage ~3 ans vs DHS 2018 — documenté comme limite sur `built_density` (v1).
- **GHSL 2015** : epoch la plus proche de DHS 2018 (pas de 5 ans) — utilisé en v2/v3.
- **CHIRPS 2018** : aligné sur l'année d'enquête DHS ; saison humide nord = mars–novembre.

---

## Choix méthodologiques

### Échelle et CRS

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `export_scale` | **1 000 m** | Résolution cible du projet (~500 m–1 km) ; compromis quotas GEE / signal |
| `crs` | **EPSG:32633** | UTM 33N, adapté au Cameroun |
| Reprojection | Par composite puis stack final | Alignement pixel à pixel avant `reduceRegions` |

### Buffers DHS (Notebook 01)

| Type grappe | Rayon buffer | CRS buffers |
|-------------|--------------|-------------|
| Urbain | **2 km** | EPSG:32633 (création) → WGS84 (stockage) |
| Rural | **5 km** | idem |

`reduceRegions` applique le reducer **mean** sur chaque polygone buffer à 1 000 m (`export_scale`) en EPSG:32633.

### Extraction par grappe

```
configs/gee.yaml
       │
       ▼
composites/  →  S2, VIIRS, DEM, WorldPop, GHSL/WorldCover, CHIRPS (v3), OSM
       │
       ▼
stack.py  →  Image 10–13 bandes + QA (ndwi, evi)
       │
       ├── mode clusters : AOI = emprise des grappes (+0.25° marge)
       │                 reduceRegions → cluster_features_gee.parquet
       │
       └── mode national : AOI = Cameroun (LSIB) → export Asset/Drive
```

### Post-traitement

1. Renommage bandes → colonnes modèle (`postprocess.py`)
2. Conversion distances m → km (/1000)
3. Imputation résiduelle des NaN (`extract_clusters.py`) — voir limites
4. Contrôles QA (`qa.py`) — plages, valeurs manquantes

### Paramètres GEE utiles

```yaml
tile_scale: 4          # parallélisme reduceRegions
max_pixels: 1000000000
max_distance_m: 50000  # plafond distances OSM (50 km)
```

---

## Reproduction de l'extraction

### Prérequis

```bash
# Environnement
.\.venv\Scripts\pip install earthengine-api geopandas pyyaml

# Authentification (une fois)
.\.venv\Scripts\earthengine.exe authenticate
```

Configurer `gee.project_id: "cameroon-poverty-mapping"` dans `configs/gee.yaml`.

### Étape 0 — Préparer les écoles HOT/OSM

```bash
# Télécharge automatiquement depuis HDX si absent, ou utilise data/raw/hotosm/
.\.venv\Scripts\python.exe scripts/prepare_hotosm_schools.py
```

Sortie : `data/processed/hotosm_cmr_education_points.geojson` (10 186 points).

### Étape 1 — Dry-run (sans appel GEE lourd)

```bash
.\.venv\Scripts\python.exe scripts/extract_gee_features.py --dry-run --mode clusters
```

### Étape 2 — Extraction test (10 grappes, bbox Yaoundé ou emprise)

```bash
.\.venv\Scripts\python.exe scripts/extract_gee_features.py --mode test \
  --output data/processed/features/cluster_features_gee_test.parquet
```

### Étape 3 — Extraction complète (toutes les grappes)

```bash
.\.venv\Scripts\python.exe scripts/extract_gee_features.py --mode clusters \
  --clusters data/processed/dhs_prepared_with_buffers.parquet \
  --output data/processed/features/cluster_features_gee.parquet
```

Durée observée (50 grappes fictives) : **~3–9 min** selon cache GEE.

### Étape 4 — Intégration Notebook 02

Dans `configs/default.yaml` :

```yaml
features:
  fake: false
  source: "gee"
  gee_parquet: "data/processed/features/cluster_features_gee.parquet"
```

```bash
.\.venv\Scripts\python.exe scripts/run_notebook_02_pipeline.py
```

### Smoke test composites (Phase 1)

```bash
.\.venv\Scripts\python.exe -m src.features.gee.smoke_test
```

### Journalisation

Chaque exécution écrit `logs/gee_run_<timestamp>.json` :
- hash de `configs/gee.yaml`
- mode, nombre de grappes, chemin sortie
- rapport QA (si extraction réussie)

---

## Résultats de la phase de validation (50 grappes fictives)

| Indicateur | Valeur |
|------------|--------|
| Grappes extraites | 50 / 50 |
| Valeurs manquantes | 0 (après imputation) |
| QA `dist_school_km` | min 1.5 km, max 50 km, 23 valeurs uniques |
| QA globale | **passed: true** (juin 2026, avec écoles HOT) |
| Importance `dist_school_km` (NB02) | gain ≈ 3.2 (3ᵉ feature, vs 0 avant HOT) |

---

## Limites connues

| Limite | Impact | Atténuation / prochaine action |
|--------|--------|--------------------------------|
| **Nuages (Sud)** | NDVI/NDBI parfois masqués | Médiane multi-annuelle ; imputation 0 documentée |
| **VIIRS NASA/002** | Production (juil. 2026) | `Gap_Filled_DNB_BRDF_Corrected_NTL`, qualité {0,1} |
| **OSM routes (GRIP4)** | Routes ≠ OSM local fin | Acceptable à 1 km ; v2 possible avec OSM natif |
| **Santé (Healthsites)** | Couverture inégale en zone rurale | Plafond 50 km ; vérifier par région |
| **Écoles (HOT)** | Couverture OSM variable, snapshot juin 2026 | Rafraîchir HDX ; envisager upload Asset GEE projet |
| **WorldCover 2021 vs DHS 2018** | `built_density` décalé temporellement | Documenter ; GHSL 2018 en v2 |
| **`built_density` faible à 1 km** | Beaucoup de 0 dans buffers ruraux | Résolution 100 m ou fraction à 500 m en v2 |
| **Imputation NaN** | Masque trous de couverture | Journaliser avec vraies DHS ; réduire imputation |
| **VIIRS saturation urbaine** | Compression dynamique en ville | Interprétation prudente |
| **Quotas GEE** | Timeouts sur AOIs vastes | `tile_scale` ; AOI = emprise grappes (pas tout le pays en clusters) |
| **50 grappes fictives** | Métriques OOF non représentatives | Validation réelle sur DHS 2018 |

---

## Structure du code

```
src/features/gee/
├── client.py              # initialize_gee, get_test_aoi
├── config.py              # load_gee_config, validation
├── stack.py               # build_feature_image (10 bandes)
├── extract_clusters.py    # reduceRegions, AOI, imputation
├── postprocess.py         # schéma Notebook 02
├── qa.py                  # contrôles plages
├── smoke_test.py          # test Yaoundé
├── composites/
│   ├── sentinel2.py
│   ├── viirs.py
│   ├── dem.py
│   ├── worldpop.py
│   ├── landcover.py
│   ├── ghsl.py
│   ├── chirps.py
│   └── osm.py             # GRIP4, Healthsites, HOT schools
└── ...

scripts/
├── prepare_hotosm_schools.py
├── extract_gee_features.py
└── run_notebook_02_pipeline.py

configs/gee.yaml
```

**Déprécié :** `src/data/gee/` → utiliser `src/features/gee/`.

---

## Prochaines étapes pour les vraies grappes DHS 2018

### 1. Modifications code attendues

| Composant | Action |
|-----------|--------|
| `src/data/load_dhs.py` | Remplacer le mode fictif par chargement réel (`HR`, `GE`, `WI`…) |
| `src/data/prepare_labels.py` | Buffers 2/5 km sur vraies coordonnées ; **appliquer le jitter DHS** |
| `data/processed/dhs_prepared_with_buffers.parquet` | Régénérer depuis NB01 avec vraies grappes |
| `scripts/extract_gee_features.py --mode clusters` | Relancer sur le nouveau parquet (~300+ grappes) |
| `configs/default.yaml` | Conserver `features.fake: false` |
| `src/features/gee/extract_clusters.py` | Réduire l'imputation silencieuse ; loguer les grappes imputées |
| VIIRS | ✅ `NASA/VIIRS/002/VNP46A2` (gap-filled, qualité {0,1}) |
| Écoles HOT | Rafraîchir export HDX ; optionnel : upload Asset GEE projet |

### 2. Gestion du jitter DHS

Les coordonnées GPS DHS sont **déplacées aléatoirement** (1–2 km urbain, jusqu'à 5 km rural) pour protéger la confidentialité.

**Recommandations :**

1. **Ne pas « dé-jitter »** les points — utiliser les coordonnées publiées telles quelles.
2. Créer les **buffers autour des points jitterés** (déjà la pratique du pipeline).
3. Documenter dans NB01 :
   - rayon de jitter par type urbain/rural (selon guide DHS Cameroun 2018)
   - que `reduceRegions` moyenne sur le buffer, pas sur un point exact
4. Vérifier que le buffer englobe le jitter maximal (2 km urbain / 5 km rural → cohérent).
5. Optionnel (analyse) : sensibilité en comparant extraction sur buffer vs disque minimal.

**À implémenter (suggestion) :**

```python
# src/data/prepare_labels.py (futur)
def apply_dhs_jitter_policy(gdf, urban_km=2, rural_km=5):
    """Documente et valide que buffer_km >= jitter max DHS."""
    ...
```

### 3. Checklist de validation (vraies DHS)

#### Avant extraction GEE

- [ ] Nombre de grappes Cameroun 2018 attendu (~300–350 selon fichiers)
- [ ] `wealth_index` sans NaN
- [ ] `urban_rural` ∈ {urban, rural}
- [ ] CRS WGS84, géométries valides
- [ ] Buffers 2 km / 5 km créés en EPSG:32633
- [ ] Carte de contrôle : grappes + buffers sur fond Cameroun
- [ ] `prepare_hotosm_schools.py` exécuté (écoles à jour)

#### Extraction GEE

- [ ] `extract_gee_features.py --dry-run --mode clusters` OK
- [ ] Extraction complète sans erreur
- [ ] `logs/gee_run_*.json` → QA `passed: true`
- [ ] 0 NaN dans `cluster_features_gee.parquet` (ou journal d'imputation < 5 %)
- [ ] `dist_school_km` : nunique > 50, min < 5 km sur au moins 10 % des grappes
- [ ] Distributions par région : pas de colonne constante

#### Intégration modèle (NB02)

- [ ] `load_cluster_features()` → source `gee`, jointure 1:1 sur `cluster_id`
- [ ] Corrélations features ↔ `wealth_index` plausibles (signe, ordre de grandeur)
- [ ] CV spatiale : stratégie block ou region documentée
- [ ] R² OOF > baseline fake (objectif minimal)
- [ ] `dist_school_km` : gain LightGBM > 0
- [ ] Sauvegarde `cv_metrics.json`, `feature_importance_gain.csv`

#### Documentation

- [ ] Mettre à jour ce fichier avec statistiques finales DHS réelles
- [ ] Noter date snapshot HOT/OSM et version WorldCover

---

## Références

- [DHS Program — GPS datasets](https://dhsprogram.com/data/dataset-admin/index.cfm)
- [HOT Education Facilities Cameroon (HDX)](https://data.humdata.org/dataset/hotosm_cmr_education_facilities)
- [GEE Community Catalog — GRIP4, Healthsites](https://gee-community-catalog.org/)
- Projet : `documentation/methodology.md`, `documentation/limitations.md`

---

*Dernière mise à jour : juin 2026 — phase GEE validée sur grappes fictives, prête pour DHS 2018 réelles.*