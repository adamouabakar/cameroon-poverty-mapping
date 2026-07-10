# Protocole de validation terrain — Cameroun

Modèle exploratoire pour partenaires locaux (INS, universités, ONG).

## Objectif

Comparer les **cartes estimées** (wealth raster 1 km, priorisation) à des **observations de terrain** ou enquêtes administratives, sans prétendre à une validation statistique exhaustive.

## Zones test recommandées (5–10 sites)

| Critère | Exemple |
|---------|---------|
| Urbain riche | Yaoundé centre, Douala |
| Urbain pauvre | Quartiers périphériques |
| Rural accessible | Littoral, Ouest |
| Rural isolé | Nord, Est (grappes haute priorité OOF) |
| Conflit modèle/terrain | Zones à fort écart OOF résiduel |

## Variables à collecter sur site

1. **Wealth proxy** — type habitat, accès eau/électricité, biens durables (aligné DHS)
2. **Accessibilité** — distance réelle école/santé/route (GPS ou OSM terrain)
3. **Contexte** — saison, conflit, migration récente

## Grille d'évaluation (par site)

| Score | Wealth raster | Priorisation | Incertitude |
|-------|---------------|--------------|-------------|
| +2 | Concordance forte | Zone prioritaire confirmée | Incertitude élevée justifiée |
| 0 | Partiellement concordant | Neutre | — |
| -2 | Discordance majeure | Faux positif priorité | Incertitude sous-estimée |

## Livrables partenaires

- Fiche site (formulaire CSV : `documentation/templates/field_validation_site.csv`)
- Photos géotaggées (optionnel)
- Rapport synthèse : `outputs/reports/field_validation_YYYY.json`

## Contact données

Les cartes nationales sont dans `outputs/maps/` :

- `wealth_index_predicted_1km_model.tif`
- `priority_index_1km.tif`
- `wealth_uncertainty_1km_model.tif`

**Ne pas utiliser pour allocation budgétaire sans validation locale complète.**