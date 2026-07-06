\# Workflow : Intégration d'une nouvelle feature GEE



\## Objectif

Ce workflow définit les étapes standards à suivre pour intégrer proprement une nouvelle feature dans un pipeline GEE (ex: GHSL, CHIRPS, Sentinel-1, etc.).



\## Étapes du Workflow



\### Étape 1 : Analyse

\- Comprendre la feature à intégrer (source, résolution, période, etc.)

\- Analyser l’impact sur le pipeline existant

\- Décider de la stratégie de version (`feature\_set`)



\### Étape 2 : Création du module

\- Créer un nouveau fichier dans `src/features/gee/composites/`

\- Suivre les conventions existantes (`reproject\_to\_target`, config-driven, etc.)

\- Bien nommer la/les bande(s) produite(s)



\### Étape 3 : Mise à jour de la configuration

\- Ajouter la section correspondante dans `configs/gee.yaml`

\- Mettre à jour `feature\_set` si nécessaire



\### Étape 4 : Intégration dans le pipeline

\- Modifier `stack.py` pour inclure la nouvelle feature de façon conditionnelle

\- Gérer correctement le nom des bandes



\### Étape 5 : Tests \& Validation

\- Mettre à jour ou créer des tests unitaires

\- Faire un dry-run

\- Faire une extraction réelle sur un petit échantillon



\### Étape 6 : Documentation

\- Mettre à jour `documentation/gee\_features.md`

\- Ajouter des explications dans le Notebook 02 si pertinent



\### Étape 7 : Comparaison (si applicable)

\- Comparer les performances avant/après (vX vs vX+1)

\- Analyser l’importance de la nouvelle feature



\## Agents impliqués

\- Feature Integration Agent (responsable principal)

\- Modeling \& Notebook Agent (si mise à jour du notebook)

\- Quality \& Testing Agent (si création de tests)

\- Master Orchestrator (supervision)



\## Règles

\- Toujours maintenir la \*\*rétrocompatibilité\*\* quand c’est possible

\- Documenter les choix techniques

\- Ne jamais casser l’existant sans solution de repli

