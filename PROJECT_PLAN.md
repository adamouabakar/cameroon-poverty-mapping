# PROJECT_PLAN — Cameroon Poverty Mapping

*Planning ambitieux — 5 jalons · juillet 2026*

## Vision

Pipeline open-source reproductible pour estimer le bien-être économique au Cameroun (~1 km), validé sur DHS 2018, enrichi INS/ECAM 4, avec interface web et outils décisionnels pour partenaires.

## Jalons

| # | Jalon | Agent | Livrables clés | Statut |
|---|-------|-------|----------------|--------|
| 1 | Fondations & gouvernance | `jalon1_fondations.md` | CI, backlog, README, structure, credentials | ✅ |
| 2 | Interface beta | `jalon2_interface.md` | Carte SHAP, incertitude, sélecteur admin | 🔄 |
| 3 | Features avancées | `jalon3_features.md` | Feature set v5, comparaison v4/v5 | ⏳ |
| 4 | Outils décisionnels | `jalon4_fonctionnalites.md` | PDF, mode terrain, simulateur | ⏳ |
| 5 | Déploiement | `jalon5_deploiement.md` | Release v1.0, site public, communication | ✅ |
| 6 | Modèle temporel | `jalon6_modele_temporel.md` | Panel 2014–2022, animation, `site/temporal.html` | ✅ |
| 7 | Plateforme finale | `jalon7_plateforme_finale.md` | Release v2.0, doc complète, communication | ✅ |

## Phases techniques (réalisées)

| Phase | Contenu | Version |
|-------|---------|---------|
| Phase 1 | DHS 430 grappes + GEE v3 + raster 1 km | v0.3 |
| Phase INS | ECAM 4 + validation externe + modèle v4 | v0.4 |
| Phase Web | Partner pack + GitHub Pages | v0.4 |
| Phase Jalons | Interface v2 + v5 + outils + release | v1.0 |

## Structure des dossiers

```
data/raw/dhs/          # Microdonnées DHS (gitignored)
data/raw/ins/          # PDF/CSV INS (gitignored)
data/reference/ins/    # Indicateurs ECAM 4 versionnés
data/processed/        # Parquets générés
outputs/maps/          # GeoTIFF + PNG
outputs/reports/       # Métriques, jalons, SHAP
figures/               # Aperçus README
site/                  # Carte web GitHub Pages
partner_pack/          # Brief partenaires
```

## Commandes orchestrateur

```bash
python scripts/run_jalon.py --jalon 1   # exécute un jalon
python scripts/run_pipeline.py          # pipeline ML v4
python scripts/build_partner_web.py     # site + pack
make test && make pipeline
```

## Références

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — bilan technique
- [`PROJECT_BACKLOG.md`](PROJECT_BACKLOG.md) — backlog jalons
- [`src/agents/master_orchestrator_jalons.md`](src/agents/master_orchestrator_jalons.md)