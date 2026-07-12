# Brief partenaire — Cameroun (DHS 2018)

## En une phrase

Estimations **exploratoires** de bien-être relatif à ~1 km, calibrées sur l'indice de richesse des grappes DHS, croisées avec des données satellitaires ouvertes. **Ce n'est pas** une statistique officielle de l'INS.

## Performance modèle (OOF, CV spatiale)

| Métrique | Valeur |
|----------|--------|
| R² OOF | 0.8084900748057773 |
| Spearman OOF | 0.8989568915489291 |
| RMSE | 36899.14013617368 |
| Grappes | 430 |
| CV | block |
| Unités wealth | zscore |

## Comment lire la carte

1. Commencer par la couche **richesse** (vue large).
2. Croiser **toujours** l'incertitude (légende toujours visible sur le site).
3. La couche **priorisation** est un indice composite exploratoire (pauvreté estimée + accessibilité OSM) — **non opérationnel**, pas un classement de villages.
4. Ne pas interpréter au niveau ménage / village (jitter GPS DHS).

## Ce que nous demandons en atelier

- Feedback : zones où la carte contredit le savoir local.
- Discussion sur l'incertitude et les limites.
- Si pertinent : validation terrain selon `field_validation_protocol.md` (pas de collecte non autorisée).

## Référence institutionnelle (INS)

Les statistiques officielles du Cameroun relèvent de l'**Institut National de la Statistique (INS) du Cameroun** :  
https://ins-cameroun.cm/  
(Contact public site : infos@ins-cameroun.cm)

Producteur des statistiques officielles ; référence pour toute décision de politique. Ce projet est exploratoire et ne se substitue pas à l'INS.

Ce projet est un **complément méthodologique exploratoire** (proxy géospatial + DHS).  
Il ne remplace pas les publications INS (ECAM, annuaires, etc.) et vise un dialogue  
méthodologique avec les producteurs officiels.

## Contact (mainteneur open source)

abubakradamou@gmail.com — délai de réponse non garanti.

## Interdits d'usage

Ces cartes ne doivent pas servir au ciblage de ménages, villages ou
individus, ni remplacer les statistiques officielles. Toute décision
opérationnelle exige validation locale et sources institutionnelles.

