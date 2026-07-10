# Guide de transposition — autre pays DHS

Checklist pour adapter le pipeline Cameroon Poverty Mapping à un autre pays.

## Prérequis

| Élément | Action |
|---------|--------|
| Enquête DHS | Télécharger HR + GPS (autorisation requise) |
| `configs/default.yaml` | `country`, `dhs_year`, chemins DHS |
| `configs/gee.yaml` | `country_filter_value`, bbox export national |
| Écoles OSM | Préparer GeoJSON HOT/OSM si absent dans GEE |

## Étapes pipeline

```bash
# 1. Préparer grappes DHS
python scripts/prepare_real_dhs_clusters.py --country XX --year YYYY

# 2. Features grappes GEE v3
python scripts/extract_gee_features.py --mode clusters --feature-set v3 \
  --clusters data/processed/dhs_clusters_XX.parquet

# 3. Modèle + évaluation
python scripts/run_real_model_evaluation.py

# 4. Export national GEE → Drive
python scripts/extract_gee_features.py --mode national --feature-set v3 --destination drive

# 5. Téléchargement tuiles + inférence
python scripts/finalize_national_coverage.py

# 6. Priorisation + incertitude
python scripts/run_prioritization_maps.py
python scripts/run_national_uncertainty.py
```

## Paramètres à recalibrer

- `gee.test_aoi.bbox` — zone test pour smoke tests
- `prioritization_criteria.yaml` — pondérations selon contexte pays
- CV spatiale : vérifier nombre de grappes (block CV vs region CV)

## Pays candidats (Afrique centrale)

| Pays | DHS récent | Notes |
|------|------------|-------|
| République démocratique du Congo | 2013–14 | Grande superficie, tuiles nombreuses |
| Gabon | 2019–21 | Peu de grappes, validation régionale |
| Tchad | 2014–15 | Couverture sahélienne |

## Tests

```bash
python -m pytest tests/ -q
```

Adapter les tests d'intégration DHS si nouveau pays de référence.