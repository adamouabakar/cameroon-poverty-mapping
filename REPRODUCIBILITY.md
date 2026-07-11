# Guide de reproductibilité

Ce document décrit comment reproduire les résultats du projet **de bout en bout**, sur Windows, Linux ou macOS.

*Dernière mise à jour : juillet 2026 — pipeline v4 (GEE v3 + INS ECAM 4).*

---

## 1. Prérequis

| Élément | Détail |
|---------|--------|
| Python | ≥ 3.10 |
| Git | Pour cloner le dépôt |
| Compte GEE | [Inscription](https://earthengine.google.com/) + `earthengine authenticate` |
| Données DHS | Cameroun 2018 — [DHS Program](https://dhsprogram.com/data/dataset/Cameroon_Standard-DHS_2018.cfm) |
| Indicateurs INS | Inclus : `data/reference/ins/ecam4_regional_indicators.csv` |

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

### Windows

```powershell
.\.venv\Scripts\activate
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\earthengine.exe authenticate
```

### Linux / macOS (ou Make)

```bash
make install
source .venv/bin/activate
earthengine authenticate
```

Éditer `configs/gee.yaml` :

```yaml
gee:
  project_id: "votre-projet-gee"
```

---

## 3. Pipeline automatisé (v4 — recommandé)

```bash
python scripts/run_pipeline.py
# ou : make pipeline
```

### Étapes détaillées

| # | Étape | Script | Sortie principale |
|---|-------|--------|-------------------|
| 1 | DHS | `prepare_real_dhs_clusters.py` | `data/processed/dhs_clusters_real.parquet` |
| 2 | GEE v3 | `extract_gee_features.py --mode clusters --feature-set v3` | `data/processed/features/cluster_features_gee_real.parquet` |
| 3 | INS + v4 | `run_ins_integration_pipeline.py` | `data/processed/features/cluster_features_gee_ins_v4.parquet` |
| 4 | Modèle v4 | `run_model_v4_evaluation.py` | `models/wealth_model_lgbm_v0_gee_v4.pkl`, `outputs/reports/model_v4_results.json` |
| 5 | Inférence | `run_national_inference_v4.py` | `outputs/maps/wealth_index_predicted_1km_model_v4.tif` |
| 6 | Cartes | `generate_results_v4_visualizations.py` | `outputs/maps/`, `outputs/reports/final_results_summary.md` |

### Options utiles

```bash
# Données déjà préparées
python scripts/run_pipeline.py --skip-dhs --skip-gee --skip-ins

# Cartes uniquement
python scripts/make_maps.py
python scripts/run_pipeline.py --only maps

# Pipeline legacy v3 (sans INS)
python scripts/run_pipeline.py --v3

# Dry-run GEE (sans appel serveur)
python scripts/extract_gee_features.py --dry-run --mode clusters --feature-set v3 \
  --clusters data/processed/dhs_clusters_real.parquet
```

---

## 4. Vérification des résultats

### Métriques attendues (v4, `random_state: 42`)

| Métrique | Valeur cible |
|----------|--------------|
| Grappes | 430 |
| R² OOF | ≈ 0.79 |
| Spearman OOF | ≈ 0.89 |
| Δ R² v4 − v3 | ≈ +0.007 |

### Validation externe INS

| Métrique | Valeur cible |
|----------|--------------|
| Spearman wealth ↔ pauvreté INS | ≈ −0.84 |
| Régions | 12 |

```bash
python -m pytest tests/ -q    # 88 tests
```

### Fichiers de contrôle

- `outputs/reports/model_v4_results.json`
- `outputs/reports/ins_external_validation.json`
- `outputs/reports/dhs_real_qa.json` (`n_clusters: 430`)
- `outputs/reports/gee_extraction_real_qa.json` (`qa_passed: true`)

---

## 5. Inférence nationale (carte raster 1 km)

### Prérequis : mosaic GEE national

```bash
python scripts/download_gee_raster_local.py --mode national --tiles
python scripts/finalize_national_coverage.py
# → data/processed/rasters/cm_features_1km_v3.tif
```

### Inférence v4 (GEE + INS régional)

```bash
python scripts/run_national_inference_v4.py
python scripts/run_national_uncertainty.py \
  --wealth outputs/maps/wealth_index_predicted_1km_model_v4.tif
python scripts/run_prioritization_maps.py \
  --wealth outputs/maps/wealth_index_predicted_1km_model_v4.tif
```

Ou en une commande :

```bash
python scripts/make_maps.py --with-inference
```

### Mode interpolation (sans raster GEE)

```bash
python scripts/run_national_inference.py --mode interpolate
```

Produit `outputs/maps/wealth_index_predicted_1km.tif` par interpolation RBF depuis les 430 grappes.

---

## 6. Configuration

| Fichier | Rôle |
|---------|------|
| `configs/default.yaml` | Pipeline global (feature_set v4, modèle) |
| `configs/gee.yaml` | Sources GEE, feature_sets v1–v3 |
| `configs/prioritization_criteria.yaml` | Indice de priorisation |

---

## 7. Données non versionnées

Le `.gitignore` exclut :

- `data/raw/` — DHS, PDF INS
- `data/processed/` — parquets et rasters générés
- `outputs/`, `logs/` — résultats locaux
- `.venv/` — environnement Python

Les **aperçus** pour le README sont versionnés dans `figures/`.

---

## 8. Dépannage

| Problème | Solution |
|----------|----------|
| `earthengine` non authentifié | `earthengine authenticate` |
| Fichiers DHS introuvables | Vérifier `CMGE71FL/` et `CMHR71DT/` |
| Raster GEE absent | `download_gee_raster_local.py --mode national` |
| Timeout GEE (430 grappes) | Augmenter `tile_scale` dans `configs/gee.yaml` |
| Chemins Windows | Utiliser chemins relatifs ou `.as_posix()` |

---

## 9. Citation et contact

Voir [`CITATION.cff`](CITATION.cff) et [`documentation/limitations.md`](documentation/limitations.md).