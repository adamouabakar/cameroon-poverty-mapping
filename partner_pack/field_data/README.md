# field_data — observations terrain (MVP)

## Fichiers

| Fichier | Rôle |
|---------|------|
| `sites.csv` | **À créer** à partir du template (copier `../field_validation_template.csv`) |
| `sites.example.csv` | Exemple de forme (données fictives d’illustration, **pas** terrain réel) |

## Colonnes

`site_id,region,lat,lon,predicted_wealth_bin,uncertainty_bin,local_assessment,notes,observer,date`

- Bins : `bas` \| `moyen` \| `haut`
- `local_assessment` : `plus pauvre` \| `similaire` \| `plus aisé`
- Les lignes `site_id` commençant par `ex` sont ignorées (template)

## Confidentialité

Si les sites ne doivent pas être publics : **ne pas committer** `sites.csv` — joindre le fichier à l’issue GitHub #1 en privé / hors repo.
