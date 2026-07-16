"""Tests limites admin DHS."""

from __future__ import annotations

import json
from pathlib import Path

from src.reports.admin_boundaries import write_dhs_region_geojson

ROOT = Path(__file__).resolve().parents[1]


def test_write_dhs_region_geojson(tmp_path: Path):
    out = tmp_path / "regions.geojson"
    write_dhs_region_geojson(out)
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 10