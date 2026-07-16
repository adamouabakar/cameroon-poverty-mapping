"""Limites administratives DHS approximatives (bounding boxes)."""

from __future__ import annotations

import json
from pathlib import Path

from src.reports.region_stats import REGION_BOUNDS


def write_dhs_region_geojson(output_path: Path) -> Path:
    """Écrit un GeoJSON FeatureCollection à partir de REGION_BOUNDS."""
    features = []
    for name, ((lat_lo, lon_lo), (lat_hi, lon_hi)) in REGION_BOUNDS.items():
        features.append(
            {
                "type": "Feature",
                "properties": {"region": name, "source": "REGION_BOUNDS"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon_lo, lat_lo],
                            [lon_hi, lat_lo],
                            [lon_hi, lat_hi],
                            [lon_lo, lat_hi],
                            [lon_lo, lat_lo],
                        ]
                    ],
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")
    return output_path