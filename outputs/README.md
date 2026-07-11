# Outputs

Généré par le pipeline — non versionné par défaut (voir `.gitignore`).

Les **aperçus** pour le README sont copiés dans `figures/` via `scripts/sync_figures.py`.

```
outputs/
├── maps/           # Cartes PNG + GeoTIFF (v4 : *_v4.*)
└── reports/        # Métriques, QA, synthèses
```

### Artefacts v4 principaux

| Fichier | Description |
|---------|-------------|
| `maps/wealth_index_predicted_1km_model_v4.tif` | Wealth national 1 km |
| `maps/wealth_uncertainty_1km_model_v4.tif` | Incertitude OOF |
| `maps/priority_index_1km_v4.tif` | Priorisation |
| `reports/model_v4_results.json` | Métriques v4 |
| `reports/final_results_summary.md` | Synthèse actionnable |

Régénération :

```bash
python scripts/make_maps.py
python scripts/sync_figures.py
```