"""Tests ECAM5 loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ins.load_ecam5 import load_ecam5_contextual_data, microdata_availability_report

ROOT = Path(__file__).resolve().parents[1]


def test_load_ecam5_reference_csv(tmp_path: Path):
    df = load_ecam5_contextual_data(
        raw_path=ROOT / "data/reference/ins/ecam5_regional_indicators.csv",
        output_path=tmp_path / "ecam5.parquet",
        project_root=ROOT,
    )
    assert len(df) == 12
    assert "poverty_rate_pct" in df.columns
    assert df["source_survey"].iloc[0] == "ECAM5"


def test_microdata_report():
    rep = microdata_availability_report()
    assert rep["ecam5_unit_records"]["publicly_available"] is False
    assert "DHS" in rep["public_microdata_proxy"]["source"]