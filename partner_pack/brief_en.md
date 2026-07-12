# Partner brief — Cameroun (DHS 2018)

## In one sentence

**Exploratory** relative-wellbeing estimates at ~1 km, calibrated on DHS cluster wealth
and open satellite/geospatial features. **Not** official INS poverty statistics.

Exploratory estimates only (DHS 2018). Not official INS stats. No household or village targeting. National/regional overview only — always check uncertainty.

## Model performance (OOF, spatial CV)

| Metric | Value |
|--------|-------|
| R² OOF | 0.8084900748057773 |
| Spearman OOF | 0.8989568915489291 |
| RMSE | 36899.14013617368 |
| Clusters | 430 |
| CV | block |
| Wealth units | zscore |

Metrics are read at build time from the project results JSON via `configs/claims.yaml`
(`metrics_keys`). They must match the published model run — not hand-copied.

## How to read the map

1. Start with the **wealth** layer (broad national/regional view only).
2. **Always** cross-check **uncertainty** (legend stays visible on the web map).
3. The **prioritization** layer is an exploratory composite (estimated deprivation + OSM
   accessibility) — **non-operational**, not a village ranking.
4. Do not interpret at household/village scale (DHS GPS jitter).

## Map link

- Live map: https://adamouabakar.github.io/cameroon-poverty-mapping/
- Offline: open `site/index.html` from `partner_pack/offline_bundle.zip`

## Institutional reference (INS)

Official statistics in Cameroon are produced by the **Institut National de la Statistique (INS) du Cameroun**:  
https://ins-cameroun.cm/  
(Public contact: infos@ins-cameroun.cm)

This open-source project is an **exploratory methodological complement** (geospatial  
proxy + DHS). It does **not** replace official INS publications (e.g. ECAM) and is  
intended for methodological dialogue with official producers.

## Contact (open-source maintainer)

abubakradamou@gmail.com — response time not guaranteed.

## Usage restrictions

Do not use these maps for household, village, or individual targeting,
or as a substitute for official national statistics. Operational decisions
require local validation and institutional sources.
