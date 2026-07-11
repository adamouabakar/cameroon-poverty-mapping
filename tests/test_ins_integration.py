"""Tests intégration INS — harmonisation et validation externe."""

from pathlib import Path

import pandas as pd
import pytest

from src.ins.load_ins import clean_ins_data, load_raw_ins_csv
from src.ins.regions import harmonize_region_name, map_dhs_to_ins
from src.ins.validate_external import build_validation_table, compute_validation_metrics

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = PROJECT_ROOT / "data/reference/ins/ecam4_regional_indicators.csv"


def test_harmonize_region_names():
    assert harmonize_region_name(pd.Series(["EXTREME-NORD", "littoral"])).tolist() == [
        "Extrême-Nord",
        "Littoral",
    ]
    assert map_dhs_to_ins("DOUALA") == "Douala"


@pytest.mark.skipif(not RAW_CSV.exists(), reason="INS raw CSV missing")
def test_load_and_clean_ins():
    df = clean_ins_data(load_raw_ins_csv(RAW_CSV))
    assert len(df) == 12
    assert df["poverty_rate_pct"].between(0, 100).all()


def test_validation_metrics_synthetic():
    regional = pd.DataFrame(
        {
            "region": ["Nord", "Centre", "Sud"],
            "n_clusters": [30, 40, 25],
            "mean_predicted_wealth": [-50000.0, 50000.0, 10000.0],
            "std_predicted_wealth": [1000.0, 1000.0, 1000.0],
            "median_predicted_wealth": [-50000.0, 50000.0, 10000.0],
        }
    )
    ins = pd.DataFrame(
        {
            "region_dhs": ["Nord", "Centre", "Sud"],
            "poverty_rate_pct": [60.0, 15.0, 25.0],
            "literacy_rate_15plus_pct": [40.0, 80.0, 70.0],
            "electricity_access_pct": [20.0, 70.0, 40.0],
            "primary_enrollment_pct": [80.0, 90.0, 85.0],
            "source_survey": ["ECAM4"] * 3,
            "source_year": [2014] * 3,
        }
    )
    table = build_validation_table(regional, ins)
    metrics = compute_validation_metrics(table)
    assert metrics["n_regions"] == 3
    assert metrics["spearman_wealth_vs_poverty"] < 0