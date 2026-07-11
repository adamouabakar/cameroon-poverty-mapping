#!/usr/bin/env python
"""Calcule SHAP summary pour modèle v4 (échantillon grappes)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_notebook_02_pipeline import FEATURE_COLUMNS_BY_SET  # noqa: E402
from src.models.save_load import load_model  # noqa: E402

MODEL = PROJECT_ROOT / "models/wealth_model_lgbm_v0_gee_v4.pkl"
FEATURES = PROJECT_ROOT / "data/processed/final_features_v4.parquet"
OUT_JSON = PROJECT_ROOT / "outputs/reports/shap_summary_v4.json"
OUT_PNG = PROJECT_ROOT / "outputs/reports/shap_beeswarm_v4.png"
MAX_SAMPLES = 120


def main() -> int:
    import shap

    df = pd.read_parquet(FEATURES)
    cols = FEATURE_COLUMNS_BY_SET["v4"]
    X = df[cols].astype(float)
    if len(X) > MAX_SAMPLES:
        X = X.sample(MAX_SAMPLES, random_state=42)

    model = load_model(MODEL)
    explainer = shap.TreeExplainer(model.model)
    sv = explainer.shap_values(X)

    mean_abs = np.abs(sv).mean(axis=0)
    ranking = sorted(zip(cols, mean_abs.tolist()), key=lambda x: x[1], reverse=True)

    ins_cols = [c for c in cols if c.startswith("ins_")]
    ins_ranking = [(f, v) for f, v in ranking if f in ins_cols]

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": str(MODEL.name),
        "n_samples": len(X),
        "top10_mean_abs_shap": [
            {"feature": f, "mean_abs_shap": round(v, 4)} for f, v in ranking[:10]
        ],
        "ins_features": [
            {"feature": f, "mean_abs_shap": round(v, 4)} for f, v in ins_ranking
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    shap.summary_plot(sv, X, show=False, max_display=15)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"✅ SHAP v4 : {OUT_JSON}")
    print(f"   Plot    : {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())