# Données

## Structure

```
data/
├── raw/
│   └── dhs/              # Microdonnées DHS (NON versionnées — licence restreinte)
│       ├── CMGE71FL/     # GPS grappes (shapefile)
│       └── CMHR71DT/     # Household Recode (.DTA)
└── processed/            # Généré par le pipeline (NON versionné)
    ├── dhs_clusters_real.parquet
    ├── features/
    │   └── cluster_features_gee_real.parquet
    └── training/
        ├── training_matrix.parquet
        └── oof_predictions.parquet
```

## Accès DHS

Demande d'accès : [DHS Program — Cameroun 2018](https://dhsprogram.com/data/dataset/Cameroon_Standard-DHS_2018.cfm)

## Génération

```bash
python scripts/run_pipeline.py
```