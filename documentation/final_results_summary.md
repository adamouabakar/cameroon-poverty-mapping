# Synthèse des résultats — Cartographie de la pauvreté, Cameroun 2018

*Version canonique — voir aussi `outputs/reports/final_results_summary.md` (généré automatiquement)*

## Métriques OOF (v3, 430 grappes réelles)

| Métrique | Valeur |
|----------|--------|
| R² OOF | 0.776 |
| Spearman OOF | 0.875 |
| RMSE OOF | 39 939 |
| MAE OOF | 30 660 |
| CV | block |

## Features les plus importantes

| Rang | Feature | Type |
|------|---------|------|
| 1 | `night_lights_mean` | Base/OSM |
| 2 | `precip_annual_mm` | CHIRPS |
| 3 | `pop_density` | Base/OSM |
| 4 | `dist_road_km` | Base/OSM |
| 5 | `ghsl_built_fraction` | GHSL |

## Interprétation

- **Luminosité nocturne** et **population** : urbanisation et activité économique.
- **GHSL** : corrélation la plus forte avec wealth (r ≈ 0.74).
- **CHIRPS** : précipitations annuelles — 2ᵉ en importance sur données réelles.
- **Distances** OSM : accès aux infrastructures.

## Comparaison v2 vs v3 (réel)

- Δ R² : **+0.070**
- Δ Spearman : **+0.036**

## Visualisations

- Scatter OOF : `outputs/reports/oof_scatter_viz.png`
- Importance : `outputs/reports/feature_importance_top15.png`
- Carte nationale : `outputs/maps/wealth_national_clusters.png`
- Raster 1 km : `outputs/maps/wealth_index_predicted_1km.tif`

## Limites

Voir [`limitations.md`](limitations.md) — jitter DHS, interpolation raster, usage exploratoire uniquement.