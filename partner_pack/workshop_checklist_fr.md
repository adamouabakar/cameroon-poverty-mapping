# Checklist atelier — validation terrain MVP (45–90 min)

## Avant l’atelier

- [ ] `configs/claims.yaml` : `contact_email` réel (pas `example.com`)
- [ ] Rebuild pack : `python scripts/build_partner_web.py`
- [ ] Envoyer email (`email_prise_de_contact_fr.md`) + lien carte + `offline_bundle.zip` si bas débit
- [ ] Partenaire nommé (org + personne) — noter en privé si sensible
- [ ] Date / heure / durée réservées

**Carte live :** https://adamouabakar.github.io/cameroon-poverty-mapping/

## Agenda suggéré

| Min | Activité |
|-----|----------|
| 0–10 | Contexte : proxy DHS, pas INS, pas de ciblage |
| 10–25 | Parcourir carte (wealth → uncertainty → priorisation non opérationnelle) |
| 25–50 | Choisir ≥5 lieux connus ; remplir CSV ensemble |
| 50–70 | Discussion écarts (où ça marche / échoue) |
| 70–90 | Suite : note d’écarts, pas d’usage budgétaire seul |

## Pendant

- [ ] Rappel éthique dit à voix haute
- [ ] CSV : ≥5 lignes (pas de lignes `ex*`)
- [ ] Bins wealth/uncertainty : `bas` \| `moyen` \| `haut`
- [ ] `local_assessment` : `plus pauvre` \| `similaire` \| `plus aisé`
- [ ] lat/lon si possible (GPS ou point carte approximatif)

## Après

```bash
# Valider CSV + échantillonner rasters + générer note
python scripts/run_field_validation_report.py \
  --csv partner_pack/field_data/sites.csv \
  --partner "NOM ORG / personne" \
  --workshop-date YYYY-MM-DD \
  --workshop-minutes 60 \
  --region "Littoral" \
  --notes "notes libres atelier"
```

- [ ] Compléter sections prose de `outputs/reports/field_validation_YYYY-MM-DD.md`
- [ ] Commit CSV (si public) + rapport **ou** joindre à l’issue GitHub #1
- [ ] Commenter l’issue #1 : date atelier, n sites, lien rapport
- [ ] Fermer #1 quand critères d’acceptation remplis

## Fichiers

| Fichier | Rôle |
|---------|------|
| `field_validation_template.csv` | En-têtes + exemple `ex1` (ignoré par le script) |
| `field_data/sites.csv` | Données réelles (≥5 sites) |
| `field_data/discrepancy_note_TEMPLATE.md` | Aide rédaction |
| `workshop_checklist_fr.md` | Ce fichier |
