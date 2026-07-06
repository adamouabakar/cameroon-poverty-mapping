# État de l’art — Cartographie de la pauvreté par imagerie satellitaire et apprentissage automatique en Afrique

## 1. Introduction

L’estimation spatiale de la pauvreté en Afrique subsaharienne repose traditionnellement sur des enquêtes ménages (DHS, MICS) et des statistiques administratives. Ces sources fournissent des mesures fiables, mais restent **géographiquement éparses** et insuffisantes pour produire une cartographie continue à l’échelle infra-administrative.

Depuis une dizaine d’années, une littérature croissante propose d’exploiter l’**imagerie satellitaire** et l’**apprentissage automatique** pour estimer des indicateurs de bien-être à partir de signaux observables (luminosité nocturne, texture du paysage, densité bâtie, accessibilité aux infrastructures). L’hypothèse centrale est qu’une partie de la variance du bien-être économique se reflète dans ces variables géospatiales, permettant une **interpolation spatiale continue** une fois le modèle ancré sur des données de terrain. Ces approches ne mesurent pas directement la pauvreté ; elles produisent des **estimations probabilistes** dont la validité dépend fortement du contexte, de la résolution et de la qualité des données d’apprentissage.

## 2. Travaux fondateurs

### Jean et al. (2016)
L’article de **Jean et al. (2016)** dans *Science* constitue la contribution fondatrice du domaine. Les auteurs combinent imagerie satellitaire diurne, luminosité nocturne (VIIRS/DMSP) et, dans certains cas, données de téléphonie mobile pour prédire l’indice de richesse DHS au niveau des grappes. Ils utilisent un réseau de neurones convolutif (CNN) pour extraire des représentations spatiales, suivies d’un modèle de régression. Appliqué à plusieurs pays africains, ce travail démontre la faisabilité d’une prédiction à résolution fine à partir de données satellitaires.

Cependant, le cadre empirique reste limité à quelques pays et mobilise parfois des données propriétaires.

> Jean, N., Burke, M., Xie, M., Davis, W. M., Lobell, D. B., & Ermon, S. (2016). Combining satellite imagery and machine learning to predict poverty. *Science*, 353(6301), 790–794. https://doi.org/10.1126/science.aaf7894

### Yeh et al. (2020)
**Yeh et al. (2020)**, dans *Nature Communications*, généralisent l’approche à **l’échelle du continent africain** en utilisant exclusivement des **données ouvertes** (Sentinel-2, Landsat, VIIRS, DHS). Un CNN est entraîné pour prédire l’indice de richesse des grappes, puis appliqué par tuiles pour générer des cartes à environ 2,4 km de résolution sur l’ensemble de l’Afrique subsaharienne, y compris le Cameroun. Ce travail établit un **standard de reproductibilité** important grâce à la mise à disposition du code et des données.

> Yeh, C., Perez, A., Driscoll, A., Azzari, G., Tang, Z., Lobell, D., … Burke, M. (2020). Using publicly available satellite imagery and deep learning to understand economic well-being in Africa. *Nature Communications*, 11, 2583. https://doi.org/10.1038/s41467-020-16185-w

## 3. Évolutions et approches hybrides

La littérature s’est ensuite diversifiée autour de deux axes principaux : l’enrichissement des variables explicatives et l’évolution des architectures de modélisation.

### Combinaison d’imagerie et de features tabulaires
Plusieurs études montrent que l’imagerie seule est souvent insuffisante, particulièrement en milieu rural. L’ajout de variables **tabulaires ou vectorielles** (luminosité nocturne, densité de population WorldPop, distances aux routes via OpenStreetMap, topographie) améliore fréquemment les performances. **Head et al. (2019)** démontrent que des combinaisons de données publiques peuvent rivaliser avec des sources plus coûteuses. **Christiaensen et al. (2021)** proposent une approche de *transfer learning* entre images haute et moyenne résolution.

> Head, A., Manguin, M., Bengio, E., & Mueller, A. (2019). Global poverty estimation using private and public data. *Nature Communications*, 10, 4783. https://doi.org/10.1038/s41467-019-12565-0  
> Christiaensen, L., Lange, S., & Wang, Q. (2021). Poverty mapping using CNNs trained on high and medium resolution satellite images, with a transfer learning approach. *Remote Sensing of Environment*, 258, 112366. https://doi.org/10.1016/j.rse.2021.112366

### CNN versus modèles tabulaires
Les approches basées sur **CNN** apprennent automatiquement des représentations spatiales, mais sont coûteuses en calcul et en données. Les modèles **tabulaires** (XGBoost, LightGBM) s’appuient sur des descripteurs pré-calculés et offrent souvent un meilleur compromis performance/interprétabilité/coût, surtout à résolution modérée (500 m – 2 km). Les travaux les plus robustes combinent généralement les deux approches avec une validation croisée spatiale rigoureuse.

## 4. Limites actuelles des méthodes

**Asymétrie urbain/rural** : Les modèles performent généralement mieux en zones urbaines, où les signaux de densité bâtie et de luminosité nocturne sont plus discriminants. En milieu rural, dominant au Cameroun, les signaux satellitaires sont plus faibles et les performances chutent souvent.

**Jitter GPS des grappes DHS** : Pour protéger la confidentialité des répondants, le programme DHS déplace aléatoirement les coordonnées des grappes (jusqu’à 2 km en zone urbaine, 5 km en zone rurale, et jusqu’à 10 km pour 1 % des grappes). Ce bruit limite fortement la résolution effective des modèles et peut induire une fausse précision s’il n’est pas correctement pris en compte (Graetz et al., 2018).

**Transférabilité inter-pays** : Un modèle entraîné à l’échelle continentale ne se généralise pas automatiquement à un pays spécifique. Les différences d’occupation du sol, de morphologie urbaine et de structure économique créent des *domain shifts* qui dégradent les performances.

**Incertitude et usage** : Beaucoup de travaux rapportent des métriques globales sans produire de **cartes d’incertitude** ni encadrer clairement les usages possibles des résultats.

## 5. Travaux spécifiques au Cameroun et à l’Afrique de l’Ouest

Au Cameroun, la connaissance du bien-être repose principalement sur les vagues DHS (2011 et 2018) et les statistiques de l’Institut National de la Statistique (INS), qui fournissent des profils régionaux robustes mais rarement des surfaces continues à haute résolution.

À notre connaissance, il n’existe pas de cartographie nationale camerounaise à ~500 m–1 km fondée exclusivement sur des données ouvertes, validée par validation croisée spatiale et accompagnée d’une documentation transparente des limites. Le Cameroun apparaît surtout comme un pays inclus dans les modèles pan-africains (Yeh et al., 2020), sans faire l’objet d’une étude dédiée approfondie.

## 6. Positionnement de ce projet

Ce projet s’inscrit dans la lignée de **Jean et al. (2016)** et **Yeh et al. (2020)**, tout en apportant plusieurs contributions spécifiques au contexte camerounais :

- **Focus national** : Entraînement et validation dédiés au Cameroun plutôt que réutilisation de prédictions continentales.
- **Données exclusivement ouvertes** et pipeline reproductible sans infrastructure lourde.
- **Résolution intermédiaire** (~500 m – 1 km) tenant explicitement compte des contraintes du jitter DHS.
- **Phase de priorisation spatiale** : traduction des cartes de bien-être en indices composites exploratoires.
- **Documentation rigoureuse des limites** : cartes d’incertitude, validation spatiale, et avertissements clairs sur l’usage exploratoire.

L’objectif est de produire un **outil d’exploration spatiale** rigoureusement documenté, en complément des sources officielles, pour combler un manque identifié au Cameroun.