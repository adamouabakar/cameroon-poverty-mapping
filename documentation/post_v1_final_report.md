# Rapport final Post-v1.0 — Cameroon Poverty Mapping

*Généré le 2026-07-12 00:14 UTC*

## Synthèse exécutive

Cinq actions post-v1.0 ont été exécutées séquentiellement avec **données publiques uniquement** (DHS 2018, INS ECAM 4/5, GEE, OSM, WorldPop).

| Action | Résultat clé |
|--------|--------------|
| 1 Validation terrain proxy | 12 sites DHS; Spearman raster↔DHS 0.958 |
| 2 ECAM 5 | Spearman modèle↔pauvreté ECAM5 -0.881 |
| 3 Modèle v5_post | R² OOF 0.8085 (+0.0151 vs v4) |
| 4 Actionnabilité | 30 grappes priorisées |
| 5 Publication | Ce rapport + brouillons communication |

## Action 1 — Validation terrain (proxy)

- Référence : wealth_index DHS 2018 aux centroides de grappes
- Concordance bins match : 33.3%
- Limite : proxy numérique, pas d'atelier partenaire terrain

## Action 2 — ECAM 5 + micro-données

- Table régionale ECAM5 intégrée (`data/reference/ins/ecam5_regional_indicators.csv`)
- Micro-données ECAM5 unitaires : **non publiques** — proxy DHS 430 grappes
- Validation externe ECAM5 : Spearman -0.881

## Action 3 — Modèle v5_post

- Features : 24 (GEE v3 + INS ECAM5 + proxies temporels/accessibilité)
- Production candidate : **v5_post**
- R² 0.8085, Spearman 0.8990

## Action 4 — Cartes + actionnabilité

- Raster priorité actionable généré
- Indice actionnabilité grappes = priorité × accessibilité × confiance OOF

### Top 5 grappes actionnables

| Région | Cluster | Indice |
|--------|---------|--------|
| Adamaoua | 276 | 0.585 |
| Nord | 377 | 0.5644 |
| Adamaoua | 344 | 0.5548 |
| Extrême-Nord | 215 | 0.5522 |
| Adamaoua | 171 | 0.5508 |

## Limites & éthique

- Estimations exploratoires — ne remplacent pas l'INS
- Pas de ciblage ménage/village/budget
- ECAM5 méthodologie EHCVM ≠ ECAM4
- Validation terrain partenaire toujours requise

## Liens

- Carte : https://adamouabakar.github.io/cameroon-poverty-mapping/
- Code : https://github.com/adamouabakar/cameroon-poverty-mapping
- Release v1.0 : https://github.com/adamouabakar/cameroon-poverty-mapping/releases/tag/v1.0.0

