# État de l’art — Cartographie de la pauvreté par imagerie satellitaire et apprentissage automatique en Afrique

## 1. Introduction

L’estimation spatiale de la pauvreté en Afrique subsaharienne repose sur des enquêtes ménages (DHS, MICS) et des statistiques administratives. Ces sources offrent des mesures fiables, mais restent **géographiquement éparses** et insuffisantes pour une cartographie continue à l’échelle infra-administrative.

Depuis une dizaine d’années, une littérature en expansion propose d’exploiter l’**imagerie satellitaire** et l’**apprentissage automatique** pour inférer des indicateurs de bien-être à partir de signaux observables : luminosité nocturne, texture de l’occupation du sol, densité bâtie, accessibilité aux infrastructures. L’hypothèse centrale — empiriquement validée dans plusieurs contextes — est qu’une partie de la variance du bien-être économique se reflète dans ces variables, permettant une **interpolation spatiale continue** lorsqu’on l’ancre sur des enquêtes de terrain. Ces approches ne mesurent pas la pauvreté directement ; elles produisent des **estimations probabilistes** dont la validité dépend du contexte, de la résolution et de la qualité des données d’apprentissage.

## 2. Travaux fondateurs

### Jean et al. (2016)

L’article de **Jean et al. (2016)** dans *Science* constitue la référence inaugurale. Les auteurs combinent imagerie satellitaire diurne, luminosité nocturne (VIIRS/DMSP) et données de téléphonie mobile pour prédire l’indice de richesse DHS au niveau des grappes. Un CNN extrait des représentations compactes de l’imagerie, puis des modèles de régression (ridge) effectuent la prédiction. Appliqué à cinq pays (dont le Nigeria, la Tanzanie et l’Ouganda), ce travail démontre des corrélations spatiales significatives et la faisabilité d’une extrapolation à résolution fine.

Son cadre empirique reste limité, mobilise parfois des données propriétaires et ne quantifie que partiellement l’incertitude.

> Jean, N., Burke, M., Xie, M., Davis, W. M., Lobell, D. B., & Ermon, S. (2016). Combining satellite imagery and machine learning to predict poverty. *Science*, 353(6301), 790–794. https://doi.org/10.1126/science.aaf7894

### Yeh et al. (2020)

**Yeh et al. (2020)**, dans *Nature Communications*, prolongent cette approche à l’**échelle continentale** avec des **données exclusivement ouvertes** (Sentinel-2, Landsat, VIIRS, DHS) et un code public. Un CNN prédit l’indice de richesse des grappes, puis le modèle est appliqué par tuiles pour produire des cartes à ~2,4 km sur l’Afrique subsaharienne, **y compris le Cameroun**. Les performances varient selon les pays (R² souvent entre 0,4 et 0,6 à l’échelle des grappes), mais l’article établit un **standard reproductible** qui structure le champ depuis.

> Yeh, C., Perez, A., Driscoll, A., Azzari, G., Tang, Z., Lobell, D., … Burke, M. (2020). Using publicly available satellite imagery and deep learning to understand economic well-being in Africa. *Nature Communications*, 11, 2583. https://doi.org/10.1038/s41467-020-16185-w

## 3. Évolutions et approches hybrides

La littérature s’est diversifiée selon deux axes : l’**enrichissement des prédicteurs** et le **choix de l’architecture de modélisation**.

### Imagerie et features tabulaires

Plusieurs études montrent que l’imagerie seule est insuffisante, surtout en milieu rural. L’ajout de variables **tabulaires ou vectorielles** — luminosité nocturne, densité de population (WorldPop), distance aux routes (OpenStreetMap), topographie, climat — améliore fréquemment la prédiction. **Head et al. (2019)** démontrent que des combinaisons de données publiques peuvent rivaliser avec des sources coûteuses (mobile, transactions). **Christiaensen et al. (2021)** proposent un **transfer learning** entre images haute et moyenne résolution, utile lorsque les couvertures satellitaires sont inégales.

> Head, A., Manguin, M., Bengio, E., & Mueller, A. (2019). Global poverty estimation using private and public data. *Nature Communications*, 10, 4783. https://doi.org/10.1038/s41467-019-12565-0

> Christiaensen, L., Lange, S., & Wang, Q. (2021). Poverty mapping using CNNs trained on high and medium resolution satellite images, with a transfer learning approach. *Remote Sensing of Environment*, 258, 112366. https://doi.org/10.1016/j.rse.2021.112366

### CNN versus modèles tabulaires

Les **CNN** (Yeh et al., 2020) apprennent automatiquement des représentations spatiales ; ils sont flexibles mais coûteux en calcul et en données. Les approches **tabulaires** (XGBoost, LightGBM, forêts aléatoires) s’appuient sur des descripteurs pré-calculés et offrent souvent un meilleur rapport performance/interprétabilité/coût, notamment à résolution modérée (500 m–2 km) et avec un nombre limité de grappes DHS. Les travaux les plus robustes combinent embeddings ou CNN, gradient boosting et validation croisée spatiale.

## 4. Limites actuelles des méthodes

**Asymétrie urbain/rural.** Les modèles performent mieux en zones urbaines et périurbaines, où densité bâtie et luminosité nocturne corrèlent fortement avec la richesse. En milieu rural — dominant au Cameroun — les signaux satellitaires sont plus faibles : une parcelle agricole peut correspondre à des niveaux de bien-être très différents. Yeh et al. (2020) rapportent des R² systématiquement plus faibles dans les strates rurales.

**Jitter GPS des grappes DHS.** Pour protéger la confidentialité, le programme DHS déplace aléatoirement les coordonnées des grappes (jusqu’à 2 km en zone urbaine, 5 km en zone rurale, 10 km pour 1 % des grappes). Ce bruit dégrade la correspondance pixel–grappe, limite la résolution effective et peut induire une **fausse précision** si on l’ignore (Graetz et al., 2018).

> Graetz, N., Woytovich, P., & Heft-Neal, S. (2018). Poisson regression with misclassified outcomes and covariates: a Bayesian approach applied to the spatial displacement of DHS clusters. *Journal of the Royal Statistical Society Series A*, 181(4), 1169–1188. https://doi.org/10.1111/rssa.12352

**Transférabilité inter-pays.** Un modèle entraîné continentalement ne se généralise pas mécaniquement à un pays donné. Les différences d’occupation du sol, de morphologie urbaine et de structure économique induisent des *domain shifts*. Rodriguez Castañón et al. (2023) montrent que les pays sous-représentés dans l’entraînement obtiennent des prédictions moins fiables.

> Rodríguez Castañón, C., Hirnschall, E., Grabner, M., & Klemmer, K. (2023). Machine learning and the geographical representation of developing countries for SDG prediction. *Nature Communications*, 14, 5173. https://doi.org/10.1038/s41467-023-40147-3

**Incertitude et usage opérationnel.** De nombreux travaux rapportent R² et RMSE sans produire de **cartes d’incertitude** ni borner les usages inappropriés. Or, une carte estimée par satellite n’est pas un taux de pauvreté officiel : c’est une variable latente calibrée sur un proxy (indice de richesse DHS), lui-même imparfait. La frontière entre exploration analytique et recommandation opérationnelle reste trop souvent insuffisamment documentée.

## 5. Travaux spécifiques au Cameroun et à l’Afrique de l’Ouest

Au Cameroun, la connaissance du bien-être repose sur les vagues **DHS** (2011, 2018) et les statistiques de l’INS, qui fournissent des profils régionaux robustes mais rarement des **surfaces continues à haute résolution**. Dans la lignée satellitaire, le Cameroun apparaît surtout comme cas inclus dans les modèles pan-africains (Yeh et al., 2020), non comme objet d’étude approfondi.

On ne dispose pas, à notre connaissance, d’une cartographie nationale camerounaise à 500 m–1 km, fondée exclusivement sur des données ouvertes, validée par validation croisée spatiale et accompagnée d’une documentation transparente des limites — contrairement au Nigeria, au Ghana, à la Tanzanie ou au Rwanda, plus couverts par la littérature. En Afrique de l’Ouest, des études existent (Nigeria, Ghana, Sénégal) à 1–5 km, mais le deep learning à haute résolution reste **inégalement réparti**. La diversité écologique camerounaise rend risquée toute extrapolation depuis des modèles entraînés ailleurs.

## 6. Positionnement de ce projet

Le présent projet s’inscrit dans la continuité de **Jean et al. (2016)** et **Yeh et al. (2020)** : ancrage DHS, signaux satellitaires ouverts, apprentissage supervisé et extrapolation spatiale. Il n’ambitionne pas une innovation algorithmique fondamentale, mais apporte des **contributions spécifiques** :

1. **Focus national** — Entraînement et validation dédiés au Cameroun, plutôt que réutilisation passive de prédictions continentales.
2. **Données exclusivement ouvertes** — Reproductibilité sans supercalculateur ni données propriétaires.
3. **Résolution intermédiaire (~500 m–1 km)** — Compromis explicite entre détail spatial et contraintes du jitter DHS.
4. **Priorisation spatiale** — Traduction des cartes de bien-être en indices composites exploratoires, avec critères documentés.
5. **Documentation des limites** — Cartes d’incertitude, validation croisée spatiale, avertissements sur l’usage exploratoire uniquement.

L’ambition est de produire un **outil d’exploration spatiale** rigoureusement borné, en complément des sources officielles, pour combler un vide identifié au Cameroun.