# État du projet — Cameroon Poverty Mapping

*Dernière mise à jour : juillet 2026*

---

## Bilan

Le pipeline **Phase 1 (cartographie)** est **fonctionnel et validé** sur les **430 grappes DHS Cameroun 2018** avec des performances OOF solides (R² ≈ 0.78, Spearman ≈ 0.88).

| Composant | Statut | Notes |
|-----------|--------|-------|
| Intégration DHS réelle | ✅ Terminé | 430 grappes, jitter officiel GE |
| Features GEE v1 (WorldCover) | ✅ | Feature set legacy |
| Features GEE v2 (GHSL) | ✅ | Surface bâtie 2015 |
| Features GEE v3 (GHSL + CHIRPS) | ✅ | 13 variables, production |
| Modèle LightGBM + CV spatiale | ✅ | Block CV, 5 folds |
| Évaluation OOF réelle | ✅ | `real_model_results.json` |
| Visualisations + cartes | ✅ | Nationale + 6 régions |
| Raster national 1 km | ✅ Sprint 1 | 96/96 tuiles, mosaïque GEE + inférence raster directe |
| Wealth z-score | ✅ Sprint 1 | RMSE 0.46 σ, modèle `*_zscore.pkl` |
| Phase 2 priorisation | 🔲 Planifié | Code squelette présent |
| Documentation | ✅ | README, REPRODUCIBILITY, limitations |
| Tests automatisés | ✅ | 52 passed (`make test`) |
| Automatisation | ✅ | `run_pipeline.py`, `regenerate_maps.py`, `Makefile` |
| Publication GitHub | ✅ Prêt | `adamouabakar/cameroon-poverty-mapping` ; données DHS locales requises |

---

## Métriques clés (réel, v3)

```
Grappes     : 430
R² OOF      : 0.776
Spearman    : 0.875
CV          : block
Feature set : v3 (GHSL + CHIRPS)
```

---

## Artefacts principaux

| Chemin | Description |
|--------|-------------|
| `data/processed/dhs_clusters_real.parquet` | Grappes + buffers + wealth_index |
| `data/processed/features/cluster_features_gee_real.parquet` | Features v3 |
| `models/wealth_model_lgbm_v0_gee_v3.pkl` | Modèle production |
| `outputs/reports/real_model_results.json` | Métriques complètes |
| `outputs/maps/wealth_index_predicted_1km.tif` | Carte nationale interpolée (legacy RBF) |
| `outputs/maps/wealth_index_predicted_1km_model.tif` | Carte nationale raster directe (GEE 1 km) |
| `outputs/reports/national_coverage_final.json` | Rapport couverture nationale 100 % |

---

## Feuille de route

### Court terme (manuel)

- [x] URL GitHub : `https://github.com/adamouabakar/cameroon-poverty-mapping`
- [x] Dépôt GitHub créé (vide) — `git push -u origin main` à lancer localement avec authentification
- [x] Workflow CI GitHub Actions (`.github/workflows/ci.yml`)
- [x] Dépôt Git initialisé (premier commit local)
- [x] Wealth z-score + modèle `wealth_model_lgbm_v0_gee_v3_zscore.pkl`
- [x] Export GEE national v3 → Drive COMPLETED
- [x] Téléchargement local GEE (`download_gee_raster_local.py`)
- [x] Inférence raster test + nationale complète (96/96 tuiles)
- [x] Mosaïque nationale 100% (`cm_features_1km_v3.tif`, 11.8 MB)
- [x] Standardiser `wealth_index` (z-score) pour métriques RMSE interprétables
- [ ] Migrer VIIRS vers `NASA/VIIRS/002/VNP46A2`

### Moyen terme

- [ ] Phase 2 : cartes de priorisation (écoles, santé, routes)
- [ ] Validation terrain avec partenaires camerounais (INS, universités)
- [ ] Notebook 04 inférence nationale complète
- [ ] CI GitHub Actions (pytest sans GEE)

### Long terme

- [ ] Transposition autre pays DHS (Afrique centrale)
- [ ] Publication article / rapport technique bilingue
- [ ] Interface web légère (cartes Folium hébergées)

---

## Historique des phases

| Phase | Période | Résultat |
|-------|---------|----------|
| Données fictives | Juin 2026 | Pipeline structurel validé (50 grappes) |
| GHSL v2 | Juin 2026 | Intégration surface bâtie |
| CHIRPS v3 | Juin 2026 | +3 features précipitations |
| DHS réel | Juil. 2026 | 430 grappes intégrées |
| Modèle réel | Juil. 2026 | R² 0.78 atteint |
| Finalisation | Juil. 2026 | Documentation + publication |
| Sprint 1 national | Juil. 2026 | 96 tuiles GEE, inférence raster 1 km |

---

## Équipe / agents

Pipeline développé en mode agents spécialisés : Data, GEE, Modeling, Results, Documentation. Voir [`Agents.md`](Agents.md).