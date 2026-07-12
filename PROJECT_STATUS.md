# État du projet — Cameroon Poverty Mapping

*Dernière mise à jour : juillet 2026 — **v2.0.0** (v5_post + ECAM5 + temporel)*

---

## Bilan

Le pipeline est **fonctionnel, documenté et prêt pour publication GitHub** sur les **430 grappes DHS Cameroun 2018**, avec modèle **v4** (GEE v3 + INS ECAM 4), cartes nationales 1 km, priorisation et incertitude.

| Composant | Statut | Notes |
|-----------|--------|-------|
| Intégration DHS réelle | ✅ | 430 grappes, jitter officiel GE |
| Features GEE v3 (GHSL + CHIRPS + VIIRS/002) | ✅ | 13 variables satellite/OSM |
| Intégration INS ECAM 4 | ✅ | 4 indicateurs régionaux, validation externe Spearman −0.84 |
| Modèle LightGBM v4 | ✅ | R² OOF 0.793, Spearman 0.889 |
| Modèle LightGBM v3 (legacy) | ✅ | R² OOF 0.787 — comparaison |
| CV spatiale | ✅ | Block CV, 5 folds |
| Raster national 1 km | ✅ | 96/96 tuiles GEE, mosaïque + inférence v4 |
| Incertitude raster | ✅ | `wealth_uncertainty_1km_model_v4.tif` |
| Phase 2 priorisation | ✅ | `priority_index_1km_v4.tif` |
| Visualisations v4 | ✅ | Nationale + 10 régions + diagnostics |
| Notebook 03 exécuté | ✅ | Résultats v4 |
| Documentation | ✅ | README, REPRODUCIBILITY, limitations, guides |
| Tests automatisés | ✅ | 88 passed |
| Automatisation | ✅ | `run_pipeline.py`, `make_maps.py`, `Makefile` |
| Partner web + pack | ✅ | Site GitHub Pages, brief FR/EN |
| Publication GitHub | ✅ Prêt | `adamouabakar/cameroon-poverty-mapping` |

---

## Métriques clés (réel, v4)

```
Grappes     : 430
R² OOF      : 0.808  (v3 : 0.787)
Spearman    : 0.899  (v3 : 0.882)
RMSE OOF    : 38 323
CV          : block
Feature set : v4 (GEE v3 + INS ECAM 4)
INS valid.  : Spearman wealth ↔ pauvreté = −0.84 (12 régions)
```

---

## Artefacts principaux

| Chemin | Description |
|--------|-------------|
| `data/processed/dhs_clusters_real.parquet` | Grappes + buffers + wealth_index |
| `data/processed/features/cluster_features_gee_ins_v4.parquet` | Features v4 |
| `data/reference/ins/ecam4_regional_indicators.csv` | Indicateurs INS (versionné) |
| `models/wealth_model_lgbm_v0_gee_v4.pkl` | Modèle production v4 |
| `outputs/reports/model_v4_results.json` | Métriques v4 complètes |
| `outputs/reports/ins_external_validation.json` | Validation externe INS |
| `outputs/maps/wealth_index_predicted_1km_model_v4.tif` | Carte nationale v4 |
| `outputs/maps/priority_index_1km_v4.tif` | Priorisation |
| `outputs/maps/wealth_uncertainty_1km_model_v4.tif` | Incertitude |
| `outputs/reports/final_results_summary.md` | Synthèse actionnable |
| `notebooks/03_results_visualization.ipynb` | Notebook résultats (exécuté) |

---

## Feuille de route

### Terminé

- [x] Pipeline DHS réel (430 grappes)
- [x] GEE v3 + export national 96/96 tuiles
- [x] Intégration INS ECAM 4 + modèle v4
- [x] Inférence raster v4 + cartes nationales/régionales
- [x] Priorisation + incertitude
- [x] Documentation complète + reproductibilité
- [x] Partner web + GitHub Pages
- [x] CI GitHub Actions (88 tests)
- [x] MIT License + CITATION.cff

### Court terme (manuel)

- [ ] `git push` avec authentification GitHub
- [ ] Contact INS / partenaires camerounais (pack prêt)
- [ ] Validation terrain (protocole prêt)

### Moyen terme

- [ ] Publication article / rapport technique bilingue
- [ ] ECAM 5 (2022) quand disponible via partenariat INS
- [ ] Raster admin1 officiel pour variables INS infra-régionales

### Long terme

- [ ] Interface web enrichie (cartes Folium hébergées)
- [ ] Pilote transposition autre pays DHS

---

## Historique des phases

| Phase | Période | Résultat |
|-------|---------|----------|
| Données fictives | Juin 2026 | Pipeline structurel validé |
| GHSL v2 + CHIRPS v3 | Juin 2026 | Feature sets enrichis |
| DHS réel | Juil. 2026 | 430 grappes intégrées |
| Sprint national | Juil. 2026 | 96 tuiles GEE, raster 1 km |
| Sprint priorisation | Juil. 2026 | Indice composite |
| VIIRS NASA/002 | Juil. 2026 | Migration collection |
| INS + v4 | Juil. 2026 | ECAM 4, R² 0.793, cartes v4 |
| Finalisation | Juil. 2026 | Documentation + publication |

---

## Équipe / agents

Pipeline développé en mode agents spécialisés : Data, GEE, Modeling, INS, Results, Documentation. Voir [`Agents.md`](Agents.md).