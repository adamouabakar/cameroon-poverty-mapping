#!/usr/bin/env python
"""Évaluation v5 vs v4 (features dérivées)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_notebook_02_pipeline import FEATURE_COLUMNS_BY_SET, run_pipeline  # noqa: E402

V4_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_ins_v4.parquet"
V5_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_v5.parquet"
V4_RESULTS = PROJECT_ROOT / "outputs/reports/model_v4_results.json"
OUT = PROJECT_ROOT / "outputs/reports/model_v5_results.json"

FEATURE_COLUMNS_BY_SET["v5"] = FEATURE_COLUMNS_BY_SET["v4"] + [
    "ndvi_night_interaction",
    "built_pop_interaction",
    "accessibility_index",
    "climate_stress_index",
]


def main() -> int:
    subprocess = __import__("subprocess")
    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/prepare_features_v5.py")],
        cwd=PROJECT_ROOT,
    )

    v4_metrics = json.loads(V4_RESULTS.read_text(encoding="utf-8"))["metrics_v4_oof"]
    v5 = run_pipeline(
        feature_set="v5",
        use_fake=False,
        gee_parquet=V5_PARQUET,
        save_artifacts=False,
    )
    v5_metrics = v5["metrics_oof"]
    delta = {k: round(v5_metrics[k] - v4_metrics[k], 6) for k in ("r2", "spearman", "rmse", "mae")}

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "feature_set": "v5",
        "n_features": len(FEATURE_COLUMNS_BY_SET["v5"]),
        "v5_extra": FEATURE_COLUMNS_BY_SET["v5"][17:],
        "metrics_v5_oof": v5_metrics,
        "metrics_v4_oof": v4_metrics,
        "delta_v5_minus_v4": delta,
        "note": "v5 = v4 + interactions et indices dérivés (proxy séries / accessibilité).",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"R² v4→v5 : {v4_metrics['r2']:.4f} → {v5_metrics['r2']:.4f} ({delta['r2']:+.4f})")
    print(f"Rapport : {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())