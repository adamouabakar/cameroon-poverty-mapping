# Limites, incertitude, éthique et recommandations

Les cartes de ce projet sont des **estimations exploratoires** du bien-être économique. Elles ne remplacent ni les enquêtes officielles, ni l’expertise locale, ni une validation terrain.

---

## Résultats observés sur données réelles (DHS 2018, juillet 2026)

### Modèle v4 (production — GEE v3 + INS ECAM 4)

Validation sur **430 grappes réelles**, feature set **v4** (17 variables) :

| Métrique | v3 | v4 | Interprétation |
|----------|-----|-----|----------------|
| R² OOF | 0.787 | **0.793** | Gain modeste avec INS régional |
| Spearman OOF | 0.882 | **0.889** | Fort accord sur le rang des grappes |
| RMSE OOF | 38 941 | **38 323** | Échelle hv271 brute |
| CV | Block | Block | Séparation spatiale des plis |

**Validation externe INS (12 régions, ECAM 4 2014) :**

| Métrique | Valeur |
|----------|--------|
| Spearman wealth ↔ pauvreté INS | **−0.84** |
| Spearman wealth ↔ électricité | **+0.85** |

**Observations v4 :** la luminosité nocturne et l'alphabétisation INS figurent parmi les variables les plus importantes ; les indicateurs INS sont **constants par région** — la carte raster 1 km assigne la région via la grappe DHS la plus proche ; la variabilité fine intra-régionale provient surtout du GEE.

### Limites spécifiques INS (v4)

- **Granularité régionale** : pas de résolution infra-régionale sans limites administratives rasterisées.
- **Décalage temporel** : ECAM 4 (2014) vs DHS 2018 (~4 ans).
- **Proxy différent** : wealth index DHS (actifs) ≠ pauvreté monétaire ECAM — comparer surtout les rangs régionaux.
- **Risque de redondance** : une partie du signal INS est déjà captée par GEE (nuit, routes, population).

---

## 1. Limites techniques

### Jitter GPS des grappes DHS

Les coordonnées des grappes DHS sont délibérément déplacées pour protéger la confidentialité des répondants : jusqu’à **2 km** en zone urbaine, **5 km** en zone rurale, et jusqu’à **10 km** pour environ 1 % des grappes. Cette politique fixe un **plafond à la résolution effective** du modèle : produire ou interpréter des cartes à une échelle très fine au voisinage immédiat d’une grappe surestime la précision spatiale. Même avec agrégation par buffer, la correspondance exacte entre un pixel et un ménage ou un village reste inconnue.

### Performance différenciée urbain / rural

Les performances sont **systématiquement plus faibles en milieu rural** qu’urbain (Yeh et al., 2020). En zone rurale camerounaise, les signaux satellitaires sont faibles et ambigus ; les cartes peuvent **lisser** les contrastes locaux.

### Incertitude spatiale et extrapolation

Entraîné sur quelques centaines de grappes et extrapolé sur ~475 000 km², le modèle est plus incertain dans les zones **éloignées des grappes** et les contextes écologiques peu représentés (forêt, Sahel, littoral).

### Limites de la résolution cible (500 m – 1 km)

La résolution de production (500 m à 1 km) reflète un compromis entre détail spatial et robustesse statistique. À **1 km**, la carte est cohérente avec le jitter DHS et plus stable ; à **500 m**, le gain en détail est partiellement masqué par l’incertitude de localisation des grappes. En dessous de 500 m, le pipeline n’est pas conçu pour une interprétation fiable au niveau national.

### Risque de fausse précision

Afficher une carte à résolution fine peut suggérer une exactitude que les données ne supportent pas. Les contours administratifs, les noms de villages ou les frontières visuellement nettes sur une carte ne signifient pas que l’estimation est valide à cette échelle. **Toute interprétation infra-communale ou au niveau du ménage est méthodologiquement incorrecte.**

---

## 2. Incertitude des prédictions

### Nature des cartes d’incertitude

Le projet produit des **cartes d’incertitude** accompagnant les prédictions de bien-être et de priorisation :

- **Écart-type des prédictions** — obtenu par agrégation des modèles entraînés lors de la validation croisée spatiale (approche *ensemble*) ;
- **Intervalles de confiance à 90 %** — bornes inférieure et supérieure (percentiles 5 et 95) de la distribution des prédictions par pixel.

Ces cartes quantifient la **variabilité des estimations du modèle**, non l’erreur absolue par rapport à la « vérité terrain » (inaccessible pixel par pixel).

### Facteurs augmentant l’incertitude

L’incertitude tend à être plus élevée lorsque :

| Facteur | Effet |
|---------|-------|
| **Distance aux grappes DHS** | Peu ou pas de points d’ancrage à proximité |
| **Zones sous-représentées** | Régions avec peu de grappes dans l’échantillon |
| **Milieu rural** | Signaux satellitaires faibles ou ambigus |
| **Hétérogénéité locale** | Forte variabilité du bien-être non capturée par les prédicteurs |
| **Données auxiliaires incomplètes** | OSM ou imagerie manquante, nuageuse ou obsolète |

Les utilisateurs doivent **croiser systématiquement** la carte de prédiction avec la carte d’incertitude avant toute interprétation.

### Interprétation des intervalles de confiance

Un intervalle à 90 % quantifie la variabilité **sous les hypothèses du modèle** ; ce n’est ni un taux de pauvreté officiel, ni une garantie au niveau individuel. Les intervalles **sous-estiment souvent** l’incertitude totale (jitter, biais du proxy, évolution depuis 2018).

---

## 3. Risques d’interprétation et d’usage

### Estimation écologique vs. mesure individuelle

Les cartes représentent des **estimations écologiques** : des valeurs moyennes ou attendues à l’échelle d’une zone (pixel de 500 m–1 km), calibrées sur l’indice de richesse des grappes DHS. Il est incorrect de :

- attribuer la valeur d’un pixel à un ménage ou un village spécifique ;
- classer des individus selon la couleur de la carte ;
- déduire le statut économique d’un lieu nommé sur la carte.

### Surinterprétation des cartes de priorisation

La Phase 2 combine pauvreté estimée et accessibilité aux services (écoles, santé, routes) en un **indice composite exploratoire**. Cet indice :

- ne mesure pas la causalité (une zone « prioritaire » n’est pas nécessairement celle où une intervention aura le plus d’effet) ;
- dépend des pondérations choisies, modifiables et arbitraires ;
- hérite de toutes les incertitudes de la Phase 1.

Les cartes de priorisation sont des **outils de scénarisation**, non des classements opérationnels définitifs.

### Usage inapproprié pour le ciblage direct

Il est **inapproprié** d’utiliser ces cartes pour :

- allouer des budgets ou des programmes à des villages identifiés sur la carte ;
- cibler des ménages pour des transferts sociaux ;
- justifier des décisions administratives sans validation locale ;
- remplacer les statistiques de l’INS ou les enquêtes officielles de pauvreté.

---

## 4. Considérations éthiques

### Risque de ré-identification

Même avec le jitter DHS, la combinaison de cartes fines, de données auxiliaires (OSM, noms de localités) et de zones géographiques restreintes peut, dans de **très petites aires**, faciliter une ré-identification indirecte de populations vulnérables. Ce risque augmente si les cartes sont diffusées à résolution excessive ou croisées avec d’autres bases de données.

### Responsabilité dans la diffusion

Toute diffusion doit accompagner les cartes d’avertissements explicites, éviter les résolutions sub-500 m sans analyse de confidentialité, et ne pas suggérer une autorité officielle.

### Validation terrain locale

Avant tout usage au-delà de la recherche ou de l’exploration analytique, une **validation terrain** avec des acteurs locaux, des experts du développement et des institutions nationales (INS, ministères) est indispensable. Les cartes satellites ne remplacent pas la connaissance contextuelle des réalités économiques, culturelles et institutionnelles.

---

## 5. Recommandations d’usage

### Usages appropriés

| Usage | Description |
|-------|-------------|
| **Exploration analytique** | Identifier des gradients spatiaux larges, des discontinuités régionales |
| **Planification préliminaire** | Formuler des hypothèses de ciblage à valider ensuite |
| **Recherche académique** | Comparer des méthodes, tester des scénarios, publier avec transparence |
| **Dialogue avec acteurs locaux** | Appuyer une discussion, non la remplacer |
| **Formation** | Illustrer les méthodes d’IA géospatiale pour le développement |

### Usages à éviter

- Substitution aux statistiques nationales officielles ;
- Ciblage de ménages, villages ou individus ;
- Allocation budgétaire directe sans validation ;
- Surveillance de populations ;
- Communication publique sans mention des limites et de l’incertitude.

### Collaboration recommandée

Collaboration recommandée avec l’**INS**, des **chercheurs camerounais** et des **organisations de terrain**, sans lesquels le risque de biais méthodologiques et de mauvaise interprétation locale est élevé.

---

## 6. Pistes d’amélioration et d’adaptation

### Adapter le dépôt à un autre pays

Le pipeline est conçu pour être **transposable** :

1. Remplacer les données DHS par celles du pays cible (nouvelle demande d’accès) ;
2. Ajuster les paramètres de buffer au jitter applicable ;
3. Mettre à jour la zone d’étude et les covariables dans les scripts GEE ;
4. Réentraîner et revalider par validation croisée spatiale ;
5. Documenter les performances et limites spécifiques au nouveau contexte.

Un modèle entraîné au Cameroun **ne doit pas** être appliqué directement à un autre pays sans réentraînement.

### Adapter la résolution

- **Résolution plus grossière (2–5 km)** : plus robuste statistiquement, recommandée pour des comparaisons régionales larges ;
- **Résolution plus fine (< 500 m)** : réservée aux zones tests, avec imagerie haute résolution et avertissements explicites sur le jitter ;
- Toujours produire des cartes d’incertitude à la résolution choisie.

### Réduire l’impact du jitter

Pistes méthodologiques et données alternatives :

| Piste | Description |
|-------|-------------|
| **Buffers adaptatifs** | Rayons fonction du type urbain/rural et de la densité de grappes |
| **Modélisation probabiliste** | Approches inspirées de Graetz et al. (2018) traitant le déplacement comme erreur de mesure |
| **Données complémentaires** | Enquêtes locales géoréférencées, recensements agrégés, enquêtes agricoles |
| **Validation externe** | Comparaison avec des estimations administratives ou des enquêtes indépendantes |
| **Imagerie multi-temporelle** | Réduction du bruit par agrégation temporelle des features |

Aucune de ces pistes n’élimine le jitter ; elles en **atténuent les effets** ou en documentent la sensibilité.

---

## Synthèse

Les cartes sont des **hypothèses spatiales informées par les données**, utiles pour explorer et dialoguer, mais insuffisantes pour décider seules. Toute utilisation responsable croise prédictions, incertitude, sources officielles et connaissance locale.