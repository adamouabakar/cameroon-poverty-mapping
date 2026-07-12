#!/usr/bin/env python
"""
Post-v1.0 Action 3 — Amélioration modèle v5 (séries temporelles + accessibilité).

Compare v5_post vs v4 OOF; v4 reste production si v5 ne bat pas v4.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_notebook_02_pipeline import FEATURE_COLUMNS_BY_SET, run_pipeline  # noqa: E402

V4_RESULTS = PROJECT_ROOT / "outputs/reports/model_v4_results.json"
V5_POST_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_v5_post.parquet"
OUT_JSON = PROJECT_ROOT / "outputs/reports/post_v1_action3_model_v5.json"
OUT_MD = PROJECT_ROOT / "outputs/reports/post_v1_action3_model_v5.md"

V5_POST_EXTRA = [
    "ndvi_seasonality_proxy",
    "ndvi_stability_index",
    "night_lights_per_capita",
    "built_night_trend_proxy",
    "accessibility_inverse",
    "min_service_distance_km",
    "road_access_score",
]

FEATURE_COLUMNS_BY_SET["v5_post"] = FEATURE_COLUMNS_BY_SET["v4"] + V5_POST_EXTRA


def main() -> int:
    subprocess.check_call(
        [sys.executable, str(PROJECT_ROOT / "scripts/prepare_features_v5_post.py")],
        cwd=PROJECT_ROOT,
    )

    v4_metrics = json.loads(V4_RESULTS.read_text(encoding="utf-8"))["metrics_v4_oof"]
    v5 = run_pipeline(
        feature_set="v5_post",
        use_fake=False,
        gee_parquet=V5_POST_PARQUET,
        save_artifacts=False,
    )
    v5_metrics = v5["metrics_oof"]
    delta = {k: round(v5_metrics[k] - v4_metrics[k], 6) for k in ("r2", "spearman", "rmse", "mae")}
    beats_v4 = v5_metrics["r2"] > v4_metrics["r2"] and v5_metrics["spearman"] >= v4_metrics["spearman"]

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "action": "post_v1_action3_model_v5",
        "feature_set": "v5_post",
        "base": "gee_v3 + ins_ecam5",
        "n_features": len(FEATURE_COLUMNS_BY_SET["v5_post"]),
        "v5_post_extra": V5_POST_EXTRA,
        "metrics_v5_post_oof": v5_metrics,
        "metrics_v4_oof": v4_metrics,
        "delta_v5_post_minus_v4": delta,
        "production_model": "v4" if not beats_v4 else "v5_post",
        "beats_v4": beats_v4,
        "methodology": {
            "time_series": "Proxies saisonnalité NDVI/précipitations et intensité nocturne/pop (GEE statique)",
            "accessibility": "Inverse distance moyenne, min distance services, score route",
            "ins": "ECAM5 contextual (Action 2)",
        },
        "note": (
            "v4 reste production si v5_post ne dépasse pas v4 sur R² et Spearman. "
            "Séries temporelles GEE multi-années = Action future (credentials GEE)."
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Post-v1.0 Action 3 — Modèle v5 amélioré",
        "",
        f"*Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC*",
        "",
        "## Résultats OOF",
        "",
        f"| Métrique | v4 | v5_post | Δ |",
        f"|----------|-----|---------|---|",
        f"| R² | {v4_metrics['r2']:.4f} | {v5_metrics['r2']:.4f} | {delta['r2']:+.4f} |",
        f"| Spearman | {v4_metrics['spearman']:.4f} | {v5_metrics['spearman']:.4f} | {delta['spearman']:+.4f} |",
        f"| RMSE | {v4_metrics['rmse']:.0f} | {v5_metrics['rmse']:.0f} | {delta['rmse']:+.0f} |",
        "",
        f"**Modèle production :** `{report['production_model']}`",
        "",
        "## Features ajoutées",
        "",
    ]
    for f in V5_POST_EXTRA:
        md.append(f"- `{f}`")
    md.extend(["", f"Parquet : `data/processed/features/cluster_features_v5_post.parquet`", ""])
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print("✅ Post-v1 Action 3 — évaluation v5_post terminée")
    print(f"  R² v4→v5_post : {v4_metrics['r2']:.4f} → {v5_metrics['r2']:.4f} ({delta['r2']:+.4f})")
    print(f"  Production : {report['production_model']}")
    print(f"  Rapport : {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())