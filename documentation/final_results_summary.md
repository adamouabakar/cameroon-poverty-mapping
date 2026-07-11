# Synthèse des résultats — Cartographie de la pauvreté, Cameroun

*Généré le 2026-07-11 15:50 UTC*

## Modèle v4 (DHS 2018 + GEE v3 + INS ECAM 4)

Le modèle v4 combine **13 variables satellitaires/OSM** (GEE v3) et **4 indicateurs
régionaux INS** issus de l'ECAM 4 (2014) : taux de pauvreté, alphabétisation,
accès électricité et scolarisation primaire.

### Métriques OOF (430 grappes)

| Métrique | v3 (GEE) | v4 (GEE+INS) | Δ v4−v3 |
|----------|----------|--------------|---------|
| R² | 0.7867 | 0.7934 | +0.0067 |
| Spearman | 0.8818 | 0.8886 | +0.0067 |
| RMSE | 38941 | 38323 | -618 |
| MAE | 30399 | 29504 | -895 |

- CV spatiale : **block** (430 grappes)
- Source INS : **ECAM 4** (2014), INS Cameroun

## Rôle des variables INS

| Variable INS | Interprétation |
|--------------|----------------|
| `ins_poverty_rate_pct` | Ancrage sur la pauvreté monétaire régionale officielle |
| `ins_literacy_rate_15plus_pct` | Capital humain — corrélé au wealth DHS |
| `ins_electricity_access_pct` | Proxy d'accès aux services de base |
| `ins_primary_enrollment_pct` | Scolarisation — signal complémentaire en zones rurales |

L'**alphabétisation INS** et la **luminosité nocturne** figurent parmi les variables
les plus importantes du modèle v4. Les indicateurs INS améliorent modestement les
métriques OOF (+0.007 R²) en captant la structure **régionale** non entièrement
visible dans les seules images satellite.

**Attention** : les variables INS sont **constantes par région DHS** — sur la carte
nationale 1 km, elles sont assignées via la grappe DHS la plus proche. La carte
montre surtout la variabilité **intra-régionale** portée par GEE, calibrée par le
niveau régional INS.

## Cartes produites

| Carte | Fichier |
|-------|---------|
| Wealth national v4 | `outputs/maps/wealth_index_predicted_1km_model_v4.tif` |
| Incertitude v4 | `outputs/maps/wealth_uncertainty_1km_model_v4.tif` |
| Priorisation v4 | `outputs/maps/priority_index_1km_v4.tif` |
| Grappes OOF v4 | `outputs/maps/wealth_national_clusters_v4.png` |

## Limites

- INS = agrégats régionaux (4 variables) — pas de résolution infra-régionale.
- ECAM 4 (2014) vs DHS 2018 — décalage temporel.
- Amélioration OOF peut refléter redondance avec signal déjà dans GEE (nuit, routes).
- Jitter DHS (~2 km) : les buffers de grappes ne localisent pas les ménages exactement.
- ECAM 4 (2014) vs DHS 2018 : décalage temporel de 4 ans.
- Carte raster v4 : pas de micro-données INS infra-régionales.

## Recommandations politiques

1. **Prioriser** les zones à faible wealth prédit *et* forte incertitude (Extrême-Nord,
   Adamaoua rural) pour enquêtes de validation terrain.
2. **Croiser** la carte de priorisation avec les programmes existants (électrification,
   écoles, santé) pour éviter les doublons d'intervention.
3. **Poursuivre** le partenariat INS pour ECAM 5 (2022) et données infra-régionales.
4. Ne pas utiliser ces cartes comme **seul** critère d'allocation budgétaire sans
   validation locale.

## Visualisations

| Artefact | Chemin |
|----------|--------|
| importance_v4 | `outputs\reports\feature_importance_v4_top17.png` |
| map_clusters_v4 | `outputs\maps\wealth_national_clusters_v4.png` |
| map_uncertainty_clusters_v4 | `outputs\maps\uncertainty_national_clusters_v4.png` |
| priority_preview_v4 | `outputs\maps\priority_index_1km_v4.png` |
| priority_raster_v4 | `outputs\maps\priority_index_1km_v4.tif` |
| regional_cluster_regional_Adamaoua_y_oof_pred | `outputs\maps\regional_v4\regional_Adamaoua_y_oof_pred.png` |
| regional_cluster_regional_Centre_y_oof_pred | `outputs\maps\regional_v4\regional_Centre_y_oof_pred.png` |
| regional_cluster_regional_Douala_y_oof_pred | `outputs\maps\regional_v4\regional_Douala_y_oof_pred.png` |
| regional_cluster_regional_Est_y_oof_pred | `outputs\maps\regional_v4\regional_Est_y_oof_pred.png` |
| regional_cluster_regional_Extrême-Nord_y_oof_pred | `outputs\maps\regional_v4\regional_Extrême-Nord_y_oof_pred.png` |
| regional_cluster_regional_Littoral_y_oof_pred | `outputs\maps\regional_v4\regional_Littoral_y_oof_pred.png` |
| regional_cluster_regional_Nord-Ouest_y_oof_pred | `outputs\maps\regional_v4\regional_Nord-Ouest_y_oof_pred.png` |
| regional_cluster_regional_Nord_y_oof_pred | `outputs\maps\regional_v4\regional_Nord_y_oof_pred.png` |
| regional_cluster_regional_Ouest_y_oof_pred | `outputs\maps\regional_v4\regional_Ouest_y_oof_pred.png` |
| regional_cluster_regional_Sud_y_oof_pred | `outputs\maps\regional_v4\regional_Sud_y_oof_pred.png` |
| regional_raster_regional_Adamaoua_raster_v4 | `outputs\maps\regional_v4\regional_Adamaoua_raster_v4.png` |
| regional_raster_regional_Centre_raster_v4 | `outputs\maps\regional_v4\regional_Centre_raster_v4.png` |
| regional_raster_regional_Douala_raster_v4 | `outputs\maps\regional_v4\regional_Douala_raster_v4.png` |
| regional_raster_regional_Est_raster_v4 | `outputs\maps\regional_v4\regional_Est_raster_v4.png` |
| regional_raster_regional_Extrême-Nord_raster_v4 | `outputs\maps\regional_v4\regional_Extrême-Nord_raster_v4.png` |
| regional_raster_regional_Littoral_raster_v4 | `outputs\maps\regional_v4\regional_Littoral_raster_v4.png` |
| regional_raster_regional_Nord-Ouest_raster_v4 | `outputs\maps\regional_v4\regional_Nord-Ouest_raster_v4.png` |
| regional_raster_regional_Nord_raster_v4 | `outputs\maps\regional_v4\regional_Nord_raster_v4.png` |
| regional_raster_regional_Ouest_raster_v4 | `outputs\maps\regional_v4\regional_Ouest_raster_v4.png` |
| regional_raster_regional_Sud_raster_v4 | `outputs\maps\regional_v4\regional_Sud_raster_v4.png` |
| residuals_v4 | `outputs\reports\residuals_v4.png` |
| scatter_oof_v4 | `outputs\reports\oof_scatter_v4.png` |
| uncertainty_preview_v4 | `outputs\maps\wealth_uncertainty_1km_model_v4.png` |
| uncertainty_raster_v4 | `outputs\maps\wealth_uncertainty_1km_model_v4.tif` |
| v3_vs_v4 | `outputs\reports\v3_vs_v4_metrics_viz.png` |
| wealth_preview_v4 | `outputs\maps\wealth_index_predicted_1km_model_v4.png` |
| wealth_raster_v4 | `outputs\maps\wealth_index_predicted_1km_model_v4.tif` |

## Prochaines étapes (Phase 5 — Documentation finale)

1. Rapport technique bilingue (méthode, limites, protocole de validation terrain)
2. Mise à jour README / REPRODUCIBILITY avec pipeline v4 complet
3. Publication open-source et partage avec partenaires camerounais (INS, MINPLADAT)
4. Pilote transposition autre pays DHS (`documentation/transposition_guide.md`)
