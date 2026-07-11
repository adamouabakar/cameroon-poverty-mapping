# Sources INS — données contextuelles Cameroun

Voir aussi la copie locale optionnelle : `data/raw/ins/` (gitignored).

## Source principale

| Attribut | Valeur |
|----------|--------|
| Enquête | **4e Enquête Camerounaise auprès des Ménages (ECAM 4)** |
| Producteur | **Institut National de la Statistique (INS) du Cameroun** |
| Année de référence | **2014** |
| Site | https://ins-cameroun.cm/ |

## PDF officiel (téléchargement local)

| Champ | Valeur |
|-------|--------|
| Titre | *Pauvreté et évolution du pouvoir d'achat des ménages — ECAM4* |
| URL | https://ins-cameroun.cm/wp-content/uploads/2025/06/Pauvrete_et_evolution_du_pouvoir_d_achat_des_menages_ECAM4.pdf |
| Chemin local | `data/raw/ins/ecam4_poverty_ins_2025.pdf` (gitignored) |

```bash
curl.exe -L -o data/raw/ins/ecam4_poverty_ins_2025.pdf "https://ins-cameroun.cm/wp-content/uploads/2025/06/Pauvrete_et_evolution_du_pouvoir_d_achat_des_menages_ECAM4.pdf"
```

## Notes

- Copie versionnée : `data/reference/ins/ecam4_regional_indicators.csv`
- Douala / Yaoundé : proxy ECAM Littoral / Centre (régions DHS distinctes)
- DHS 2018 vs ECAM 2014 : validation indicative (décalage temporel)