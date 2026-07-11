# AGENTS.md - Cameroon Poverty Mapping Project

## Project Overview

Open-source, reproducible pipeline to estimate poverty at fine spatial resolution (~1 km) in Cameroon using open data (DHS 2018 + satellite imagery + OSM + WorldPop + INS/ECAM 4).

**Current Status (July 2026):** **v0.4.0 — Phase 1–4 complete** — 430 clusters, GEE v3 (VIIRS/002), INS ECAM 4, LightGBM v4 R² OOF ≈ 0.79, national raster 96/96, prioritization + uncertainty maps at 1 km, documentation publication-ready.

## Tech Stack

- Python + GeoPandas + Rasterio
- Google Earth Engine (GEE) for feature extraction
- LightGBM for modeling
- Spatial cross-validation (block / region)
- INS/ECAM 4 regional indicators (v4)
- Folium / matplotlib for visualization
- Parquet + GeoJSON for data storage

## Key Deliverables

| Artifact | Path |
|----------|------|
| DHS clusters | `data/processed/dhs_clusters_real.parquet` |
| GEE features v3 | `data/processed/features/cluster_features_gee_real.parquet` |
| INS contextual | `data/processed/ins_contextual_data.parquet` |
| GEE + INS features v4 | `data/processed/features/cluster_features_gee_ins_v4.parquet` |
| Model v4 | `models/wealth_model_lgbm_v0_gee_v4.pkl` |
| Results v4 | `outputs/reports/model_v4_results.json` |
| INS validation | `outputs/reports/ins_external_validation.json` |
| National features mosaic | `data/processed/rasters/cm_features_1km_v3.tif` |
| National wealth raster v4 | `outputs/maps/wealth_index_predicted_1km_model_v4.tif` |
| Priority raster v4 | `outputs/maps/priority_index_1km_v4.tif` |
| Uncertainty raster v4 | `outputs/maps/wealth_uncertainty_1km_model_v4.tif` |
| Summary report | `outputs/reports/final_results_summary.md` |
| Maps | `outputs/maps/` |

## Pipeline Entry Points

```bash
python scripts/run_pipeline.py          # Full pipeline v4
python scripts/make_maps.py             # Regenerate maps
python scripts/regenerate_maps.py       # Alias maps
python -m pytest tests/ -q              # Tests (88)
make pipeline                           # Makefile wrapper
```

## Documentation

- `README.md` — Project overview
- `REPRODUCIBILITY.md` — Step-by-step reproduction
- `PROJECT_STATUS.md` — Status and roadmap
- `documentation/` — Methodology, limitations, GEE features, INS partners

## Priorities (post-v0.4.0)

1. Field validation with Cameroon partners (protocol ready — `documentation/field_validation_protocol.md`)
2. Publication article / rapport technique bilingue
3. INS partnership for ECAM 5 (2022) and admin boundaries
4. Transposition pilote autre pays DHS (guide ready — `documentation/transposition_guide.md`)