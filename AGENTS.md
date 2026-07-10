# AGENTS.md - Cameroon Poverty Mapping Project

## Project Overview

Open-source, reproducible pipeline to estimate poverty at fine spatial resolution (~1 km) in Cameroon using open data (DHS 2018 + satellite imagery + OSM + WorldPop).

**Current Status (July 2026):** **Phase 1 + Sprints 1–2 + VIIRS NASA/002 complete** — 430 clusters, GEE v3 (VIIRS/002), LightGBM R² OOF ≈ 0.79, national raster 96/96, prioritization + uncertainty maps at 1 km.

## Tech Stack

- Python + GeoPandas + Rasterio
- Google Earth Engine (GEE) for feature extraction
- LightGBM for modeling
- Spatial cross-validation (block / region)
- Folium / matplotlib for visualization
- Parquet + GeoJSON for data storage

## Key Deliverables

| Artifact | Path |
|----------|------|
| DHS clusters | `data/processed/dhs_clusters_real.parquet` |
| GEE features v3 | `data/processed/features/cluster_features_gee_real.parquet` |
| Model | `models/wealth_model_lgbm_v0_gee_v3.pkl` |
| Results | `outputs/reports/real_model_results.json` |
| National features mosaic | `data/processed/rasters/cm_features_1km_v3.tif` |
| National wealth raster | `outputs/maps/wealth_index_predicted_1km_model.tif` |
| Priority raster | `outputs/maps/priority_index_1km.tif` |
| Uncertainty raster | `outputs/maps/wealth_uncertainty_1km_model.tif` |
| Maps | `outputs/maps/` |

## Pipeline Entry Points

```bash
python scripts/run_pipeline.py          # Full pipeline
python scripts/regenerate_maps.py       # Maps only
python -m pytest tests/ -q            # Tests
```

## Documentation

- `README.md` — Project overview
- `REPRODUCIBILITY.md` — Step-by-step reproduction
- `PROJECT_STATUS.md` — Status and roadmap
- `documentation/` — Methodology, limitations, GEE features

## Priorities (post-v0.3.0)

1. Field validation with Cameroon partners (protocol ready — `documentation/field_validation_protocol.md`)
2. Publication article / rapport technique bilingue
3. Interface web légère (cartes Folium hébergées)
4. Transposition pilote autre pays DHS (guide ready — `documentation/transposition_guide.md`)