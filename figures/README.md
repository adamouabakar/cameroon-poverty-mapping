# Figures

Aperçus versionnés pour le README et la documentation.

| Fichier | Source | Description |
|---------|--------|-------------|
| `wealth_national_v4_preview.png` | `outputs/maps/wealth_index_predicted_1km_model_v4.png` | Carte nationale wealth v4 |
| `priority_v4_preview.png` | `outputs/maps/priority_index_1km_v4.png` | Indice de priorisation |
| `uncertainty_v4_preview.png` | `outputs/maps/wealth_uncertainty_1km_model_v4.png` | Incertitude OOF |
| `ins_validation_scatter.png` | `outputs/maps/ins_external_validation_scatter.png` | Validation externe INS |
| `wealth_national_preview.png` | legacy v3 | Ancien aperçu (conservé) |

Régénération des aperçus après nouvelles cartes :

```bash
python scripts/make_maps.py
# puis copier manuellement ou :
python scripts/sync_figures.py
```

Les cartes et graphiques complets sont dans `outputs/maps/` et `outputs/reports/` (non versionnés).