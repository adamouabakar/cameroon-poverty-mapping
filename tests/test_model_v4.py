"""Smoke tests feature set v4 modeling artifacts."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(
    not (PROJECT_ROOT / "data/processed/final_features_v4.parquet").exists(),
    reason="final_features_v4 not built",
)
def test_final_features_v4_shape():
    import pandas as pd

    df = pd.read_parquet(PROJECT_ROOT / "data/processed/final_features_v4.parquet")
    assert len(df) == 430
    ins_cols = [c for c in df.columns if c.startswith("ins_")]
    assert len(ins_cols) == 4


@pytest.mark.skipif(
    not (PROJECT_ROOT / "outputs/reports/model_v4_results.json").exists(),
    reason="model_v4_results not built",
)
def test_model_v4_beats_v3_r2():
    import json

    report = json.loads(
        (PROJECT_ROOT / "outputs/reports/model_v4_results.json").read_text(encoding="utf-8")
    )
    delta = report["comparison_v3_vs_v4"]["metrics"]["delta_v4_minus_v3"]
    assert delta["r2"] >= 0