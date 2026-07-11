# Protocole de validation terrain — Cameroun

Modèle exploratoire pour partenaires locaux (INS, universités, ONG).

## Objectif

Comparer les **cartes estimées** (wealth raster 1 km, priorisation) à des **observations de terrain** ou enquêtes administratives, sans prétendre à une validation statistique exhaustive.

## MVP (issue #1)

Minimum pour fermer le premier dialogue :

1. Un partenaire nommé + un atelier 45–90 min  
2. CSV ≥5 sites (`partner_pack/field_data/sites.csv`)  
3. Note d’écarts générée / complétée  

Checklist : `partner_pack/workshop_checklist_fr.md`.

## Zones test recommandées (5–10 sites — au-delà du MVP)

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

- Fiche site CSV : `partner_pack/field_validation_template.csv` → `partner_pack/field_data/sites.csv`
- Checklist atelier : `partner_pack/workshop_checklist_fr.md`
- Photos géotaggées (optionnel)
- Rapport :

```bash
python scripts/run_field_validation_report.py \
  --csv partner_pack/field_data/sites.csv \
  --partner "ORG / personne" \
  --workshop-date YYYY-MM-DD \
  --workshop-minutes 60 \
  --region "…"
```

Sorties : `outputs/reports/field_validation_YYYY-MM-DD.md` (+ `.json`).

## Contact données

Rasters (souvent locaux, non git) :

- `wealth_index_predicted_1km_model_z.tif` (préféré) ou `…_model.tif`
- `priority_index_1km.tif`
- `wealth_uncertainty_1km_model.tif`

Carte web : https://adamouabakar.github.io/cameroon-poverty-mapping/

**Ne pas utiliser pour allocation budgétaire sans validation locale complète.**
