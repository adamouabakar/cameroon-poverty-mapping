# Guide de reproductibilité

Ce document décrit comment reproduire les résultats du projet **de bout en bout**, sur Windows, Linux ou macOS.

---

## 1. Prérequis

| Élément | Détail |
|---------|--------|
| Python | ≥ 3.10 |
| Git | Pour cloner le dépôt |
| Compte GEE | [Inscription](https://earthengine.google.com/) + `earthengine authenticate` |
| Données DHS | Cameroun 2018 — [DHS Program](https://dhsprogram.com/data/dataset/Cameroon_Standard-DHS_2018.cfm) |

### Fichiers DHS attendus (`data/raw/dhs/`)

```
data/raw/dhs/
├── CMGE71FL/CMGE71FL.shp      # GPS grappes (shapefile)
└── CMHR71DT/CMHR71FL.DTA      # Household Recode
```

> Les microdonnées DHS ne sont **pas** incluses dans ce dépôt (licence restreinte).

---

## 2. Installation

```bash
git clone https://github.com/adamouabakar/cameroon-poverty-mapping.git
cd cameroon-poverty-mapping
python -m venv .venv
```

Ou avec **Make** (Linux/macOS, ou Windows + `make` installé) :

```bash
make install
make test        # 50 tests — données fictives isolées
make pipeline    # pipeline complet
make maps        # cartes uniquement
```

### Suite d'installation (détaillée)

```bash

# Windows
.\.venv\Scripts\activate
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\earthengine.exe authenticate

# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
earthengine authenticate
```

Éditer `configs/gee.yaml` :

```yaml
gee:
  project_id: "votre-projet-gee"
```

---

## 3. Pipeline automatisé

```bash
python scripts/run_pipeline.py
```

### Étapes détaillées

| Étape | Script | Sortie principale |
|-------|--------|-------------------|
| 1. DHS | `prepare_real_dhs_clusters.py` | `data/processed/dhs_clusters_real.parquet` |
| 2. GEE v3 | `extract_gee_features.py --mode clusters --feature-set v3` | `data/processed/features/cluster_features_gee_real.parquet` |
| 3. Modèle | `run_real_model_evaluation.py` | `outputs/reports/real_model_results.json` |
| 4. Cartes | `generate_results_visualizations.py` | `outputs/maps/`, `outputs/reports/` |

### Options utiles

```bash
# Données déjà préparées — sauter DHS et GEE
python scripts/run_pipeline.py --skip-dhs --skip-gee

# Régénérer uniquement les cartes
python scripts/regenerate_maps.py

# Dry-run GEE (sans appel serveur)
python scripts/extract_gee_features.py --dry-run --mode clusters --feature-set v3 \
  --clusters data/processed/dhs_clusters_real.parquet
```

---

## 4. Vérification des résultats

Métriques attendues (ordre de grandeur, graine fixe `random_state: 42`) :

| Métrique | Valeur cible |
|----------|--------------|
| R² OOF | ≈ 0.77–0.78 |
| Spearman OOF | ≈ 0.87–0.88 |
| Grappes | 430 |

```bash
python -m pytest tests/ -q
```

Fichiers de contrôle :

- `outputs/reports/real_model_results.json`
- `outputs/reports/gee_extraction_real_qa.json` (`qa_passed: true`)
- `outputs/reports/dhs_real_qa.json` (`n_clusters: 430`)

---

## 5. Inférence nationale (carte raster)

### Mode interpolation (immédiat, sans export GEE national)

```bash
python scripts/run_national_inference.py --mode interpolate
```

Produit `outputs/maps/wealth_index_predicted_1km.tif` par interpolation RBF depuis les 430 grappes.

### Mode raster (inférence pixel directe)

1. Exporter les features GEE nationales :

```bash
python scripts/extract_gee_features.py --mode national --feature-set v3 --destination drive
```

2. Télécharger le GeoTIFF dans `data/processed/rasters/cm_features_1km_v3.tif`

3. Inférer :

```bash
python scripts/run_national_inference.py --mode raster \
  --features data/processed/rasters/cm_features_1km_v3.tif
```

---

## 6. Configuration

| Fichier | Rôle |
|---------|------|
| `configs/default.yaml` | Pipeline global (DHS, modèle, features v3) |
| `configs/gee.yaml` | Sources GEE, feature_sets v1/v2/v3 |
| `configs/prioritization_criteria.yaml` | Phase 2 (priorisation) |

---

## 7. Données non versionnées

Le `.gitignore` exclut :

- `data/raw/` — DHS, fichiers sensibles
- `data/processed/` — parquets générés
- `outputs/`, `logs/` — résultats locaux
- `.venv/` — environnement Python

Pour publier des **échantillons** de démonstration, utiliser un dépôt séparé ou Git LFS avec données anonymisées.

---

## 8. Dépannage

| Problème | Solution |
|----------|----------|
| `earthengine` non authentifié | `earthengine authenticate` |
| Fichiers DHS introuvables | Vérifier structure `CMGE71FL/` et `CMHR71DT/` |
| Timeout GEE (430 grappes) | Augmenter `tile_scale` dans `configs/gee.yaml` |
| Chemins Windows | Utiliser des chemins relatifs ou `.as_posix()` |

---

## 9. Contact et citation

Voir [`CITATION.cff`](CITATION.cff) et [`documentation/limitations.md`](documentation/limitations.md).