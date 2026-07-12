\# Limites et Discussion Méthodologique



\## Limites identifiées



\### 1. Granularité et agrégation

\- Les variables INS (ECAM) sont principalement disponibles au niveau régional ou départemental, alors que le modèle prédit à l’échelle \~1 km. Cela crée un risque de \*\*sur-apprentissage géographique\*\* et une perte de précision locale.



\### 2. Décalage temporel

\- ECAM 4 (2014) vs DHS 2018 → décalage d’environ 4 ans. Les conditions socio-économiques ont pu évoluer, ce qui limite la précision de la validation externe.



\### 3. Proxy de richesse différent

\- La variable cible DHS (`hv271` ou richesse factorielle) n’est pas exactement équivalente à la pauvreté monétaire mesurée par l’INS (seuil de pauvreté). Les écarts absolus en pourcentage sont donc difficiles à interpréter directement.



\### 4. Qualité des données satellitaires

\- Les features GEE (notamment en zone forestière dense ou nuageuse) peuvent avoir des biais.

\- Manque de séries temporelles longues et d’embeddings profonds (CNN) pour capturer la texture urbaine/rurale fine.



\### 5. Taille de l’échantillon

\- Seulement 430 grappes DHS réelles → risque de sur-apprentissage et faible généralisation spatiale.



\### 6. Absence de validation terrain

\- Aucune vérification terrain directe n’a été effectuée pour l’instant.



\## Comparaison avec d’autres travaux



\- \*\*World Bank Poverty Maps\*\* : Approches similaires (DHS + satellite), mais souvent avec plus de données et des modèles plus complexes (Small Area Estimation).

\- \*\*Meta Relative Wealth Index\*\* : Très bon au niveau national, mais moins précis localement que notre approche hybride.

\- \*\*Travaux africains récents\*\* (ex: Stanford, Flowminder) : Utilisent souvent des données mobiles ou des CNN sur Sentinel-2, ce que nous n’avons pas encore intégré.



\*\*Positionnement de notre projet\*\* : Nous nous situons dans une bonne moyenne, avec un bon équilibre entre accessibilité des données et rigueur méthodologique, mais nous manquons encore de profondeur sur l’explicabilité spatiale et la validation terrain.



\## Recommandations pour aller plus loin



\- Intégrer ECAM 5 (2022) dès que possible.

\- Ajouter des séries temporelles et des embeddings CNN.

\- Réaliser une validation terrain ciblée dans les zones à fort écart (Extrême-Nord, Nord, Douala).

\- Développer une couche d’incertitude plus robuste (modèle probabiliste).

