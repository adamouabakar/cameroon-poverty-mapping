"""Generate notebooks/02_modeling_pipeline.ipynb."""
import json
from pathlib import Path

cells = []


def md(source: str):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": [source]})


def code(source: str):
    cells.append(
        {
            "cell_type": "code",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [line + "\n" for line in source.split("\n")],
        }
    )


md(
    """# 02 — Modeling Pipeline

**Objectif :** Entraîner et évaluer un modèle LightGBM de prédiction de l'indice de richesse (`wealth_index`), avec validation croisée spatiale et estimation conservative de l'incertitude.

---

## Entrées

| Fichier | Description |
|---------|-------------|
| `data/processed/dhs_prepared_with_buffers.parquet` | Grappes DHS + buffers (Notebook 01) |
| `data/processed/features/cluster_features_gee.parquet` | Features GEE (extraction GEE, mode `clusters`) |

## Jeu de features (v1 / v2)

| Version | Colonne bâti | Source |
|---------|--------------|--------|
| **v1** | `built_density` | WorldCover 2021 |
| **v2** | `ghsl_built_fraction` | GHSL GHS-BUILT-S 2015 |

> **Exécuter les cellules dans l'ordre** (menu *Run All*) pour éviter les erreurs de variables non définies."""
)

code(
    """import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import lightgbm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.load_training_data import build_training_matrix, load_prepared_clusters
from src.data.merge_features import merge_dhs_with_features
from src.features.load_features import load_cluster_features, resolve_feature_source
from src.models.cv_pipeline import run_spatial_cv
from src.models.evaluate import build_cv_report, compute_metrics, compute_spearman, evaluate_by_strata
from src.models.save_load import save_model
from src.models.train import extract_median_best_iteration, train_final_model
from src.models.uncertainty import attach_prediction_intervals, compute_residual_uncertainty
from src.utils.config import load_config
from src.utils.helpers import hash_config_file
from src.utils.spatial_cv import select_cv_strategy

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (10, 6)
print("✓ Imports réussis")"""
)

md("## 1. Configuration")

code(
    """# ── Paramètres modifiables ──────────────────────────────────────────────
FEATURE_SET = "v2"          # "v1" = built_density | "v2" = ghsl_built_fraction
USE_FAKE_FEATURES = False   # True = features simulées (test pipeline)

FEATURE_COLUMNS_BY_SET = {
    "v1": [
        "night_lights_mean", "ndvi_mean", "ndbi_mean",
        "dist_road_km", "dist_school_km", "dist_health_km",
        "pop_density", "elevation_m", "slope_deg", "built_density",
    ],
    "v2": [
        "night_lights_mean", "ndvi_mean", "ndbi_mean",
        "dist_road_km", "dist_school_km", "dist_health_km",
        "pop_density", "elevation_m", "slope_deg", "ghsl_built_fraction",
    ],
}

# ── Chargement config projet ────────────────────────────────────────────
config_path = PROJECT_ROOT / "configs" / "default.yaml"
config = load_config(config_path)
config_hash = hash_config_file(config_path)

# Surcharge session (notebook > default.yaml)
config["features"]["feature_set"] = FEATURE_SET
config["features"]["columns"] = FEATURE_COLUMNS_BY_SET[FEATURE_SET]
config["features"]["fake"] = USE_FAKE_FEATURES
config["features"]["source"] = "fake" if USE_FAKE_FEATURES else "gee"

feature_source = resolve_feature_source(config)
FEATURE_COLS = config["features"]["columns"]
gee_parquet_path = PROJECT_ROOT / config["features"].get(
    "gee_parquet", "data/processed/features/cluster_features_gee.parquet"
)

print(f"LightGBM version : {lightgbm.__version__}")
print(f"Config hash      : {config_hash}")
print(f"Feature set      : {FEATURE_SET}")
print(f"Feature source   : {feature_source}")
print(f"N features       : {len(FEATURE_COLS)}")
print(f"Dernière colonne : {FEATURE_COLS[-1]}")
if feature_source == "gee":
    print(f"GEE parquet      : {gee_parquet_path}")
    print(f"Parquet existe   : {gee_parquet_path.exists()}")"""
)

md("## 2. Chargement des grappes DHS")

code(
    """prepared_path = PROJECT_ROOT / config["data"]["prepared_clusters"]
gdf = load_prepared_clusters(prepared_path)

assert gdf["wealth_index"].isna().sum() == 0
assert set(gdf["urban_rural"].unique()).issubset({"urban", "rural"})
assert gdf.crs.to_epsg() == 4326

print(f"Nombre de grappes : {len(gdf)}")
print(f"Régions           : {gdf['region'].nunique()}")
gdf.head()"""
)

code(
    """title_suffix = " (fictives)" if feature_source == "fake" else ""
fig, ax = plt.subplots()
for label, subset in gdf.groupby("urban_rural"):
    ax.scatter(subset["longitude"], subset["latitude"], label=label, alpha=0.8)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title(f"Grappes DHS{title_suffix}")
ax.legend()
plt.show()"""
)

md(
    """## 3. Chargement des features + construction de `training_df`

Cette section crée **`training_df`** — table fusionnée grappes + features.
Toutes les cellules suivantes en dépendent : exécutez celle-ci avant la CV."""
)

code(
    """features_df, feature_source = load_cluster_features(gdf, config, project_root=PROJECT_ROOT)

assert len(FEATURE_COLS) == 10, f"Attendu 10 features, obtenu {len(FEATURE_COLS)}"
missing_cols = [c for c in FEATURE_COLS if c not in features_df.columns]
assert not missing_cols, f"Colonnes manquantes dans features : {missing_cols}"

training_df = merge_dhs_with_features(gdf, features_df)
assert len(training_df) == len(gdf), "Perte de grappes après fusion"

if feature_source == "fake":
    print("⚠️  Features simulées — pipeline structurel uniquement")
else:
    print("✅ Features GEE chargées depuis :", gee_parquet_path)
    print(f"   Feature set {FEATURE_SET} — colonne bâti : {FEATURE_COLS[-1]}")

print(f"training_df : {training_df.shape[0]} lignes × {training_df.shape[1]} colonnes")
features_df[FEATURE_COLS].describe().round(3)"""
)

code(
    """corr_with_target = training_df[FEATURE_COLS].corrwith(training_df["wealth_index"]).abs()
print("Corrélations absolues features ↔ wealth_index :")
print(corr_with_target.sort_values().round(3))

if feature_source == "fake":
    assert corr_with_target.max() < 0.3, "Features fictives trop corrélées à la cible"
else:
    print("Mode GEE : signal réel possible — pas de seuil de corrélation imposé.")"""
)

code(
    """X, y, meta = build_training_matrix(training_df, feature_cols=FEATURE_COLS)
print(f"X shape : {X.shape}")
print(f"y shape : {y.shape}")"""
)

code(
    """fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sns.histplot(y, kde=True, ax=axes[0])
axes[0].set_title("Distribution de wealth_index")
sns.boxplot(data=training_df, x="urban_rural", y="wealth_index", ax=axes[1])
axes[1].set_title("wealth_index par urbain/rural")
plt.tight_layout()
plt.show()"""
)

md(
    """## 4. Validation croisée spatiale

Validation par **blocs spatiaux** pour éviter le *spatial leakage*.
Repli automatique vers `region_based_cv` si les plis sont déséquilibrés."""
)

code(
    """cv_strategy, fold_ids, balance_report = select_cv_strategy(
    gdf,
    preferred=config["model"]["cv_strategy"],
    n_folds=config["model"]["n_folds"],
    random_state=config["model"]["random_state"],
)
print(f"Stratégie retenue : {cv_strategy}")
print(json.dumps(balance_report, indent=2, ensure_ascii=False))"""
)

code(
    """# Garde-fou : training_df doit exister (section 3)
if "training_df" not in globals():
    raise NameError(
        "training_df n'est pas défini. Exécutez la section 3 "
        "(Chargement des features) avant cette cellule."
    )

training_df = training_df.copy()
training_df["fold_id"] = fold_ids.values

fig, ax = plt.subplots()
scatter = ax.scatter(
    training_df["longitude"],
    training_df["latitude"],
    c=training_df["fold_id"],
    cmap="tab10",
    s=80,
)
ax.set_title(f"Grappes par pli CV ({cv_strategy})")
plt.colorbar(scatter, ax=ax, label="fold_id")
plt.show()"""
)

md("## 5. Entraînement CV + métriques OOF")

code(
    """cv_results = run_spatial_cv(
    X, y, gdf, config, cv_strategy=cv_strategy, return_models=True
)

fold_metrics_df = pd.DataFrame(cv_results.fold_metrics)
fold_metrics_df"""
)

code(
    """metrics_global = compute_metrics(y, cv_results.oof_predictions)
metrics_global["spearman"] = compute_spearman(y, cv_results.oof_predictions)
pd.DataFrame([metrics_global])"""
)

code(
    """fig, ax = plt.subplots()
ax.scatter(y, cv_results.oof_predictions, alpha=0.8)
lims = [min(y.min(), cv_results.oof_predictions.min()), max(y.max(), cv_results.oof_predictions.max())]
ax.plot(lims, lims, "r--", label="Identité")
ax.set_xlabel("wealth_index observé")
ax.set_ylabel("wealth_index prédit (OOF)")
ax.set_title(f"Prédictions OOF — R²={metrics_global['r2']:.3f}")
ax.legend()
plt.show()"""
)

code(
    """metrics_urban_rural = evaluate_by_strata(y, cv_results.oof_predictions, meta["urban_rural"])
metrics_region = evaluate_by_strata(y, cv_results.oof_predictions, meta["region"])
print("Par urbain/rural")
display(metrics_urban_rural)
print("Par région")
display(metrics_region)"""
)

code(
    """best_fold_idx = int(fold_metrics_df["rmse"].idxmin())
importance_df = cv_results.models[best_fold_idx].feature_importance()
importance_df.plot.bar(x="feature", y="gain", legend=False, title="Importance (gain LightGBM)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()
importance_df"""
)

md(
    """## 6. Incertitude (approximation conservative)

Intervalles à 90 % basés sur les résidus OOF globaux — pas une incertitude pixel."""
)

code(
    """uncertainty = compute_residual_uncertainty(cv_results.oof_residuals)
oof_df = attach_prediction_intervals(
    cv_results.oof_predictions,
    y,
    uncertainty,
    meta=meta,
)
print(json.dumps(uncertainty, indent=2, ensure_ascii=False))
oof_df.head()"""
)

code(
    """fig, axes = plt.subplots(1, 2, figsize=(12, 4))
sns.histplot(cv_results.oof_residuals, kde=True, ax=axes[0])
axes[0].set_title("Résidus OOF")
fold_metrics_df.plot.bar(x="fold", y="rmse", ax=axes[1], legend=False, title="RMSE par pli")
plt.tight_layout()
plt.show()"""
)

md("## 7. Modèle final + export")

code(
    """median_iter = extract_median_best_iteration(cv_results)
final_model = train_final_model(
    X,
    y,
    config,
    median_best_iteration=median_iter,
    strata=meta["urban_rural"],
)

models_dir = PROJECT_ROOT / config["output"]["models_dir"]
models_dir.mkdir(parents=True, exist_ok=True)
model_suffix = "fake" if feature_source == "fake" else f"gee_{FEATURE_SET}"
model_path = models_dir / f"wealth_model_lgbm_v0_{model_suffix}.pkl"
save_model(final_model, model_path)

print("⚠️  Les métriques de référence sont uniquement celles de la CV OOF.")
print(f"Modèle final sauvegardé : {model_path}")
print(f"Median best iteration  : {median_iter}")"""
)

code(
    """reports_dir = PROJECT_ROOT / config["output"]["reports_dir"]
training_dir = PROJECT_ROOT / config["data"]["training_dir"]
logs_dir = PROJECT_ROOT / config["output"]["logs_dir"]
for d in [reports_dir, training_dir, logs_dir]:
    d.mkdir(parents=True, exist_ok=True)

report = build_cv_report(
    cv_results.fold_metrics,
    metrics_global,
    config_hash=config_hash,
    cv_strategy=cv_results.cv_strategy,
    fake_data=(feature_source == "fake"),
)
report["feature_source"] = feature_source
report["feature_set"] = FEATURE_SET
report_path = reports_dir / "cv_metrics.json"
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

oof_path = training_dir / "oof_predictions.parquet"
oof_df.to_parquet(oof_path, index=False)

training_df[FEATURE_COLS + ["cluster_id", "wealth_index", "region", "urban_rural", "fold_id"]].to_parquet(
    training_dir / "training_matrix.parquet", index=False
)

importance_df.to_csv(reports_dir / "feature_importance_gain.csv", index=False)

log_payload = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "config_hash": config_hash,
    "cv_strategy": cv_results.cv_strategy,
    "feature_source": feature_source,
    "feature_set": FEATURE_SET,
    "fake_data": feature_source == "fake",
    "n_clusters": len(gdf),
    "metrics_oof": metrics_global,
}
(logs_dir / f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json").write_text(
    json.dumps(log_payload, indent=2), encoding="utf-8"
)

print(f"Rapport CV : {report_path}")
print(f"OOF preds  : {oof_path}")"""
)

code(
    """print("=== Limites selon le mode actuel ===")
print(f"Mode features : {feature_source}")
print(f"Feature set   : {FEATURE_SET} ({FEATURE_COLS[-1]})")

if feature_source == "fake":
    print("- Grappes et wealth_index simulés")
    print("- Features décorrélées de la cible (pipeline structurel)")
    print("- Métriques non interprétables scientifiquement")
else:
    print("- Labels DHS soumis au jitter GPS")
    if FEATURE_SET == "v2":
        print("- Fraction bâtie : GHSL 2015 (ghsl_built_fraction)")
    else:
        print("- Fraction bâtie : WorldCover 2021 (built_density)")
    print("- Métriques exploratoires — pas de décision opérationnelle directe")

print("- Incertitude OOF : approximation conservative (résidus globaux)")
print("- Ne pas utiliser pour ciblage individuel ou allocation budgétaire")"""
)

md(
    """## 8. Comparaison v1 vs v2 (WorldCover vs GHSL)

Exécute les deux jeux de features sur les **mêmes grappes** et compare les métriques OOF.

> Automatisation : `python scripts/compare_v1_v2_ghsl.py`"""
)

code(
    """# Comparaison objective v1 (built_density) vs v2 (ghsl_built_fraction)
# Nécessite : cluster_features_gee_v1.parquet + cluster_features_gee.parquet (v2)

import subprocess

compare_script = PROJECT_ROOT / "scripts" / "compare_v1_v2_ghsl.py"
result = subprocess.run(
    [sys.executable, str(compare_script), "--skip-extraction"],
    cwd=str(PROJECT_ROOT),
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.returncode != 0:
    print("stderr:", result.stderr)
    print("ℹ️  Si v1 parquet manquant, relancez sans --skip-extraction :")
    print(f"   python {compare_script}")

comparison_path = PROJECT_ROOT / "outputs/reports/v1_vs_v2_comparison.json"
if comparison_path.exists():
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    table = comparison["comparison_table"]
    comp_df = pd.DataFrame(table)
    display(comp_df)
    print("\\nConclusion :", comparison["conclusion"])
    print("Verdict    :", comparison["verdict"])"""
)

md(
    """## Prochaines étapes

1. Valider v1 vs v2 sur **vraies grappes DHS 2018**
2. Export raster national + cartes (Notebook 04)
3. Interprétabilité SHAP"""
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

out = Path(__file__).resolve().parent.parent / "notebooks" / "02_modeling_pipeline.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out}")