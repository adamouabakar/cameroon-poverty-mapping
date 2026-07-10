"""Generate notebooks/04_national_inference_walkthrough.ipynb."""

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
    """# 04 — Inférence nationale, priorisation et incertitude

**Objectif :** Reproduire et visualiser le pipeline post-modélisation à résolution ~1 km :

1. Couverture raster GEE v3 (VIIRS NASA/002)
2. Inférence wealth raster directe (LightGBM z-score)
3. Carte de priorisation Phase 2 (pauvreté + accessibilité OSM)
4. Carte d'incertitude OOF alignée sur la grille modèle

> Ce notebook **ne nécessite pas GEE** si les artefacts sont déjà générés localement.
> Pour régénérer les rasters : voir section « Régénération » en fin de notebook."""
)

code(
    """from pathlib import Path
import json
import sys

import pandas as pd
from IPython.display import Image, display, Markdown

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

REPORTS = PROJECT_ROOT / "outputs/reports"
MAPS = PROJECT_ROOT / "outputs/maps"
RASTERS = PROJECT_ROOT / "data/processed/rasters"

ARTIFACTS = {
    "features_mosaic": RASTERS / "cm_features_1km_v3.tif",
    "wealth_model": MAPS / "wealth_index_predicted_1km_model.tif",
    "wealth_z": MAPS / "wealth_index_predicted_1km_model_z.tif",
    "priority": MAPS / "priority_index_1km.tif",
    "uncertainty": MAPS / "wealth_uncertainty_1km_model.tif",
    "viirs_report": REPORTS / "viirs_reexport_final.json",
    "prioritization": REPORTS / "prioritization_results.json",
    "uncertainty_report": REPORTS / "national_uncertainty.json",
    "model_results": REPORTS / "real_model_results.json",
}

for name, path in ARTIFACTS.items():
    status = "✅" if path.exists() else "❌"
    size = f" ({path.stat().st_size / 1e6:.1f} MB)" if path.exists() and path.is_file() else ""
    print(f"{status} {name}: {path.name}{size}")"""
)

md("## 1. Couverture nationale (tuiles GEE)")

code(
    """import subprocess

subprocess.run(
    [sys.executable, str(PROJECT_ROOT / "scripts/check_raster_progress.py")],
    cwd=PROJECT_ROOT,
    check=False,
)"""
)

md("## 2. Métriques modèle (VIIRS NASA/002)")

code(
    """if ARTIFACTS["model_results"].exists():
    report = json.loads(ARTIFACTS["model_results"].read_text(encoding="utf-8"))
    m = report["metrics_oof"]
    print(f"R² OOF      : {m['r2']:.4f}")
    print(f"Spearman    : {m['spearman']:.4f}")
    print(f"RMSE        : {m['rmse']:.2f}")
    print(f"Feature set : {report.get('feature_set')}")
else:
    print("❌ real_model_results.json manquant — lancez run_real_model_evaluation.py")"""
)

md("## 3. Rapport ré-export VIIRS")

code(
    """if ARTIFACTS["viirs_report"].exists():
    viirs = json.loads(ARTIFACTS["viirs_report"].read_text(encoding="utf-8"))
    display(pd.Series(viirs))
else:
    print("ℹ️  viirs_reexport_final.json absent — pipeline VIIRS pas encore finalisé")"""
)

md("## 4. Carte wealth raster (inférence GEE directe)")

code(
    """wealth_png = MAPS / "wealth_index_predicted_1km_model.png"
if wealth_png.exists():
    display(Markdown("### Wealth index — raster modèle 1 km"))
    display(Image(filename=str(wealth_png)))
else:
    print("❌ Lancez : python scripts/run_national_inference.py --mode raster --features data/processed/rasters/cm_features_1km_v3.tif")"""
)

md("## 5. Carte de priorisation (Phase 2)")

code(
    """prio_png = MAPS / "priority_index_1km.png"
if ARTIFACTS["prioritization"].exists():
    prio = json.loads(ARTIFACTS["prioritization"].read_text(encoding="utf-8"))
    top = pd.DataFrame(prio["top_clusters"]).head(10)
    display(Markdown("### Top 10 grappes prioritaires"))
    display(top)
if prio_png.exists():
    display(Markdown("### Carte priorisation composite"))
    display(Image(filename=str(prio_png)))
else:
    print("❌ Lancez : python scripts/run_prioritization_maps.py")"""
)

md("## 6. Carte d'incertitude (grille modèle)")

code(
    """unc_png = MAPS / "wealth_uncertainty_1km_model.png"
if unc_png.exists():
    display(Markdown("### Incertitude OOF — demi-largeur 90 %"))
    display(Image(filename=str(unc_png)))
else:
    print("❌ Lancez : python scripts/run_national_uncertainty.py")"""
)

md(
    """## 7. Régénération complète (optionnel)

Commandes pour reconstruire tous les artefacts nationaux :

```bash
# Après export GEE + téléchargement 96 tuiles
python scripts/finalize_viirs_reexport.py

# Ou étape par étape :
python scripts/run_national_inference.py --mode raster --features data/processed/rasters/cm_features_1km_v3.tif
python scripts/run_prioritization_maps.py
python scripts/run_national_uncertainty.py
```

## Limites

- Les cartes raster sont **exploratoires** (pas de validation terrain).
- L'incertitude est une **approximation OOF globale** interpolée depuis 430 grappes.
- La priorisation combine des pondérations configurables (`configs/prioritization_criteria.yaml`)."""
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

out = Path(__file__).resolve().parent.parent / "notebooks" / "04_national_inference_walkthrough.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out}")