#!/usr/bin/env python
"""Feature set v5 = v4 + dérivées temporelles / accessibilité composite."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

V4_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_ins_v4.parquet"
OUT = PROJECT_ROOT / "data/processed/features/cluster_features_v5.parquet"

V5_EXTRA = [
    "ndvi_night_interaction",
    "built_pop_interaction",
    "accessibility_index",
    "climate_stress_index",
]


def main() -> int:
    df = pd.read_parquet(V4_PARQUET)
    out = df.copy()
    out["ndvi_night_interaction"] = out["ndvi_mean"] * out["night_lights_mean"]
    out["built_pop_interaction"] = out["ghsl_built_fraction"] * np.log1p(out["pop_density"].clip(lower=0))
    dist_cols = ["dist_road_km", "dist_school_km", "dist_health_km"]
    out["accessibility_index"] = out[dist_cols].mean(axis=1)
    out["climate_stress_index"] = out["precip_cv"] / (out["precip_annual_mm"].clip(lower=1) / 1000.0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(f"✅ features v5 : {OUT}")
    print(f"   Colonnes +{len(V5_EXTRA)} : {V5_EXTRA}")
    print(f"   Lignes : {len(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())