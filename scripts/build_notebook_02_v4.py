"""Generate notebooks/02_modeling_v4.ipynb (feature set v4 + INS)."""

import json
import uuid
from pathlib import Path

cells = []


def _cell(cell_type: str, source: str, **extra) -> dict:
    return {
        "cell_type": cell_type,
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": [line + "\n" for line in source.split("\n")],
        **extra,
    }


def md(s):
    cells.append(_cell("markdown", s))


def code(s):
    cells.append(_cell("code", s, outputs=[], execution_count=None))


md(
    """# 02 — Modélisation v4 (GEE v3 + INS ECAM 4)

**Objectif :** Entraîner LightGBM avec features satellitaires **et** indicateurs INS régionaux,
comparer les performances à v3, analyser l'importance des variables INS.

> Variables INS : jointure régionale (ECAM 4, 2014) — voir limites de leakage régional."""
)

code(
    """import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_notebook_02_pipeline import FEATURE_COLUMNS_BY_SET, run_pipeline

V4_PARQUET = PROJECT_ROOT / "data/processed/features/cluster_features_gee_ins_v4.parquet"
FINAL_PARQUET = PROJECT_ROOT / "data/processed/final_features_v4.parquet"
REPORT = PROJECT_ROOT / "outputs/reports/model_v4_results.json"

print("✓ Setup v4")"""
)

code(
    """real_v4 = run_pipeline(
    feature_set="v4",
    use_fake=False,
    gee_parquet=V4_PARQUET,
    save_artifacts=True,
)
m = real_v4["metrics_oof"]
print(f"R² OOF       : {m['r2']:.4f}")
print(f"Spearman OOF : {m['spearman']:.4f}")
print(f"RMSE OOF     : {m['rmse']:.0f}")
print(f"MAE OOF      : {m['mae']:.0f}")"""
)

code(
    """if REPORT.exists():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    comp = report["comparison_v3_vs_v4"]["metrics"]
    display(pd.DataFrame(comp).T)
    ins_imp = pd.DataFrame(report["ins_feature_importance"])
    display(ins_imp)"""
)

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "cells": cells,
}

out = Path(__file__).resolve().parent.parent / "notebooks" / "02_modeling_v4.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out}")