#!/usr/bin/env python
"""
Exécute le Notebook 02 en une seule commande.

Modes :
  notebook (défaut) — exécute notebooks/02_modeling_pipeline.ipynb via nbclient
                      et sauvegarde un notebook exécuté en sortie.
  pipeline          — exécute la logique Python directement (plus rapide, sans .ipynb).

Exemples :
  python scripts/run_notebook_02_pipeline.py
  python scripts/run_notebook_02_pipeline.py --feature-set v2
  python scripts/run_notebook_02_pipeline.py --mode pipeline --feature-set v2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Backend non interactif pour matplotlib (figures dans le notebook exécuté)
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "02_modeling_pipeline.ipynb"
DEFAULT_OUTPUT = PROJECT_ROOT / "notebooks" / "02_modeling_pipeline_executed.ipynb"

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
    "v3": [
        "night_lights_mean", "ndvi_mean", "ndbi_mean",
        "dist_road_km", "dist_school_km", "dist_health_km",
        "pop_density", "elevation_m", "slope_deg", "ghsl_built_fraction",
        "precip_annual_mm", "precip_wet_season_mm", "precip_cv",
    ],
    "v4": [
        "night_lights_mean", "ndvi_mean", "ndbi_mean",
        "dist_road_km", "dist_school_km", "dist_health_km",
        "pop_density", "elevation_m", "slope_deg", "ghsl_built_fraction",
        "precip_annual_mm", "precip_wet_season_mm", "precip_cv",
        "ins_poverty_rate_pct", "ins_literacy_rate_15plus_pct",
        "ins_electricity_access_pct", "ins_primary_enrollment_pct",
    ],
}

INS_FEATURE_COLS = [
    "ins_poverty_rate_pct", "ins_literacy_rate_15plus_pct",
    "ins_electricity_access_pct", "ins_primary_enrollment_pct",
]

GEE_PARQUET_BY_SET = {
    "v1": "data/processed/features/cluster_features_gee_v1.parquet",
    "v2": "data/processed/features/cluster_features_gee.parquet",
    "v3": "data/processed/features/cluster_features_gee_v3.parquet",
    "v4": "data/processed/features/cluster_features_gee_ins_v4.parquet",
}


def _patch_notebook_parameters(
    nb,
    feature_set: str,
    use_fake: bool,
    gee_parquet: str | None = None,
) -> None:
    """Injecte FEATURE_SET et USE_FAKE_FEATURES dans la cellule paramètres."""
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        if "FEATURE_SET" not in cell.source or "FEATURE_COLUMNS_BY_SET" not in cell.source:
            continue
        source = cell.source
        source = re.sub(
            r'FEATURE_SET\s*=\s*["\']v[123]["\']',
            f'FEATURE_SET = "{feature_set}"',
            source,
        )
        source = re.sub(
            r"USE_FAKE_FEATURES\s*=\s*(True|False)",
            f"USE_FAKE_FEATURES = {use_fake}",
            source,
        )
        if not use_fake:
            parquet = gee_parquet or GEE_PARQUET_BY_SET.get(feature_set)
            if parquet:
                parquet_posix = Path(parquet).as_posix()
                needle = 'config["features"]["source"] = "fake" if USE_FAKE_FEATURES else "gee"\n'
                if needle in source:
                    source = source.replace(
                        needle,
                        needle + f'config["features"]["gee_parquet"] = "{parquet_posix}"\n',
                    )
        cell.source = source
        return
    raise RuntimeError(
        "Cellule paramètres introuvable dans le notebook "
        "(attendu : FEATURE_SET + FEATURE_COLUMNS_BY_SET)."
    )


def _collect_notebook_errors(nb) -> list[str]:
    """Extrait les tracebacks des cellules en erreur."""
    errors = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                errors.append(
                    f"Cellule {i}: {output.get('ename')}: {output.get('evalue')}"
                )
    return errors


def run_notebook(
    feature_set: str = "v2",
    use_fake: bool = False,
    gee_parquet: str | Path | None = None,
    notebook_path: Path = NOTEBOOK_PATH,
    output_path: Path = DEFAULT_OUTPUT,
    timeout: int = 900,
) -> dict:
    """Exécute le notebook et sauvegarde la version exécutée."""
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    if not notebook_path.exists():
        raise FileNotFoundError(f"Notebook introuvable : {notebook_path}")

    print(f"📓 Notebook source : {notebook_path}")
    print(f"   Feature set      : {feature_set}")
    print(f"   Fake features    : {use_fake}")
    print(f"   Sortie           : {output_path}")

    with open(notebook_path, encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    _patch_notebook_parameters(nb, feature_set, use_fake, gee_parquet=str(gee_parquet) if gee_parquet else None)

    client = NotebookClient(
        nb,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(notebook_path.parent)}},
    )

    try:
        client.execute()
        status = "success"
        error_msg = None
    except CellExecutionError as exc:
        status = "error"
        error_msg = str(exc)
        print(f"\n❌ Erreur d'exécution notebook :\n{exc}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"💾 Notebook exécuté sauvegardé : {output_path}")

    cell_errors = _collect_notebook_errors(nb)
    summary = _load_artifacts_summary(feature_set)
    summary.update(
        {
            "status": status,
            "mode": "notebook",
            "feature_set": feature_set,
            "use_fake_features": use_fake,
            "notebook_input": str(notebook_path),
            "notebook_output": str(output_path),
            "cell_errors": cell_errors,
            "execution_error": error_msg,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    return summary


def run_pipeline(
    feature_set: str = "v2",
    use_fake: bool = False,
    gee_parquet: str | Path | None = None,
    save_artifacts: bool = True,
) -> dict:
    """Exécute la logique du notebook sans passer par .ipynb (rapide)."""
    from src.data.load_training_data import build_training_matrix, load_prepared_clusters
    from src.data.merge_features import merge_dhs_with_features
    from src.features.load_features import load_cluster_features, resolve_feature_source
    from src.models.cv_pipeline import run_spatial_cv
    from src.models.evaluate import build_cv_report, compute_metrics, compute_spearman
    from src.models.save_load import save_model
    from src.models.train import extract_median_best_iteration, train_final_model
    from src.models.uncertainty import attach_prediction_intervals, compute_residual_uncertainty
    from src.utils.config import load_config
    from src.utils.helpers import hash_config_file
    from src.utils.spatial_cv import select_cv_strategy
    import pandas as pd

    config_path = PROJECT_ROOT / "configs" / "default.yaml"
    config = load_config(config_path)
    config["features"]["feature_set"] = feature_set
    config["features"]["columns"] = FEATURE_COLUMNS_BY_SET[feature_set]
    config["features"]["fake"] = use_fake
    config["features"]["source"] = "fake" if use_fake else "gee"
    if gee_parquet is not None:
        config["features"]["gee_parquet"] = str(gee_parquet)

    feature_source = resolve_feature_source(config)
    feature_cols = config["features"]["columns"]

    gdf = load_prepared_clusters(PROJECT_ROOT / config["data"]["prepared_clusters"])
    features_df, loaded_source = load_cluster_features(gdf, config, project_root=PROJECT_ROOT)
    assert loaded_source == feature_source

    training_df = merge_dhs_with_features(gdf, features_df)
    X, y, meta = build_training_matrix(training_df, feature_cols=feature_cols)

    cv_strategy, fold_ids, balance_report = select_cv_strategy(
        gdf,
        preferred=config["model"]["cv_strategy"],
        n_folds=config["model"]["n_folds"],
        random_state=config["model"]["random_state"],
    )
    training_df = training_df.copy()
    training_df["fold_id"] = fold_ids.values

    cv_results = run_spatial_cv(
        X, y, gdf, config, cv_strategy=cv_strategy, return_models=True
    )

    metrics_global = compute_metrics(y, cv_results.oof_predictions)
    metrics_global["spearman"] = compute_spearman(y, cv_results.oof_predictions)

    fold_metrics_df = pd.DataFrame(cv_results.fold_metrics)
    best_fold_idx = int(fold_metrics_df["rmse"].idxmin())
    importance_df = cv_results.models[best_fold_idx].feature_importance()

    corr_with_target = (
        training_df[feature_cols].corrwith(training_df["wealth_index"]).abs().sort_values()
    )

    uncertainty = compute_residual_uncertainty(cv_results.oof_residuals)
    oof_df = attach_prediction_intervals(cv_results.oof_predictions, y, uncertainty, meta=meta)

    report_path = None
    if save_artifacts:
        training_dir = PROJECT_ROOT / config["data"]["training_dir"]
        reports_dir = PROJECT_ROOT / config["output"]["reports_dir"]
        models_dir = PROJECT_ROOT / config["output"]["models_dir"]
        for d in (training_dir, reports_dir, models_dir):
            d.mkdir(parents=True, exist_ok=True)

        training_df[
            feature_cols + ["cluster_id", "wealth_index", "region", "urban_rural", "fold_id"]
        ].to_parquet(training_dir / "training_matrix.parquet", index=False)
        oof_df.to_parquet(training_dir / "oof_predictions.parquet", index=False)
        importance_df.to_csv(reports_dir / "feature_importance_gain.csv", index=False)

        median_iter = extract_median_best_iteration(cv_results)
        final_model = train_final_model(
            X, y, config, median_best_iteration=median_iter, strata=meta["urban_rural"]
        )
        model_suffix = "fake" if feature_source == "fake" else f"gee_{feature_set}"
        save_model(final_model, models_dir / f"wealth_model_lgbm_v0_{model_suffix}.pkl")

        report = build_cv_report(
            cv_results.fold_metrics,
            metrics_global,
            config_hash=hash_config_file(config_path),
            cv_strategy=cv_results.cv_strategy,
            fake_data=(feature_source == "fake"),
        )
        report["feature_source"] = feature_source
        report["feature_set"] = feature_set
        report_path = reports_dir / "cv_metrics.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    result = {
        "status": "success",
        "mode": "pipeline",
        "feature_set": feature_set,
        "use_fake_features": use_fake,
        "feature_source": feature_source,
        "n_clusters": len(gdf),
        "cv_strategy": cv_strategy,
        "metrics_oof": metrics_global,
        "correlations_abs": corr_with_target.round(4).to_dict(),
        "importance_gain": importance_df.set_index("feature")["gain"].round(4).to_dict(),
        "balance_report": balance_report,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if save_artifacts:
        result["report_path"] = str(report_path)
        result["importance_path"] = str(reports_dir / "feature_importance_gain.csv")
    return result


def _load_artifacts_summary(feature_set: str) -> dict:
    """Lit les artefacts produits par le notebook (si présents)."""
    reports_dir = PROJECT_ROOT / "outputs" / "reports"
    training_dir = PROJECT_ROOT / "data" / "processed" / "training"
    summary: dict = {}

    report_path = reports_dir / "cv_metrics.json"
    if report_path.exists():
        summary["report"] = json.loads(report_path.read_text(encoding="utf-8"))
        summary["metrics_oof"] = (
            summary["report"].get("global_oof_metrics")
            or summary["report"].get("metrics_global")
            or summary["report"].get("metrics_oof")
        )
        summary["feature_source"] = summary["report"].get("feature_source")
        summary["cv_strategy"] = summary["report"].get("cv_strategy")

    importance_path = reports_dir / "feature_importance_gain.csv"
    if importance_path.exists():
        import pandas as pd

        imp = pd.read_csv(importance_path)
        if "feature" in imp.columns and "gain" in imp.columns:
            summary["importance_gain"] = (
                imp.set_index("feature")["gain"].round(4).to_dict()
            )

    matrix_path = training_dir / "training_matrix.parquet"
    if matrix_path.exists():
        import pandas as pd

        df = pd.read_parquet(matrix_path)
        built_col = FEATURE_COLUMNS_BY_SET[feature_set][-1]
        if built_col in df.columns and "wealth_index" in df.columns:
            summary["correlations_abs"] = (
                df[FEATURE_COLUMNS_BY_SET[feature_set]]
                .corrwith(df["wealth_index"])
                .abs()
                .round(4)
                .to_dict()
            )
        summary["n_clusters"] = len(df)

    return summary


def _print_summary(summary: dict) -> None:
    print("\n" + "=" * 60)
    status = summary.get("status", "unknown")
    if status == "success":
        print("✅ NOTEBOOK 02 — SUCCÈS")
    else:
        print("❌ NOTEBOOK 02 — ÉCHEC")
    print("=" * 60)
    print(f"Mode           : {summary.get('mode')}")
    print(f"Feature set    : {summary.get('feature_set')}")
    print(f"Feature source : {summary.get('feature_source', summary.get('report', {}).get('feature_source', 'n/a'))}")
    if summary.get("n_clusters"):
        print(f"Grappes        : {summary['n_clusters']}")
    if summary.get("cv_strategy"):
        print(f"CV strategy    : {summary['cv_strategy']}")
    metrics = summary.get("metrics_oof") or summary.get("report", {}).get("metrics_global")
    if metrics:
        print(f"R² OOF         : {metrics.get('r2', metrics.get('r2_oof', 'n/a'))}")
        print(f"RMSE OOF       : {metrics.get('rmse', 'n/a')}")
        print(f"Spearman OOF   : {metrics.get('spearman', 'n/a')}")
    if summary.get("notebook_output"):
        print(f"Notebook out   : {summary['notebook_output']}")
    if summary.get("report_path"):
        print(f"Rapport CV     : {summary['report_path']}")
    if summary.get("cell_errors"):
        print("\nErreurs cellules :")
        for err in summary["cell_errors"]:
            print(f"  - {err}")
    if summary.get("execution_error"):
        print(f"\nDétail : {summary['execution_error']}")
    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exécuter le Notebook 02 automatiquement")
    parser.add_argument(
        "--mode",
        choices=["notebook", "pipeline"],
        default="notebook",
        help="notebook = exécute le .ipynb | pipeline = Python direct (rapide)",
    )
    parser.add_argument(
        "--feature-set",
        choices=["v1", "v2", "v3"],
        default="v2",
        help="Jeu de features (v2 = GHSL, v3 = GHSL + CHIRPS)",
    )
    parser.add_argument(
        "--use-fake",
        action="store_true",
        help="Utiliser des features simulées au lieu du parquet GEE",
    )
    parser.add_argument(
        "--notebook",
        default=str(NOTEBOOK_PATH),
        help="Chemin vers le notebook source",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Chemin du notebook exécuté en sortie",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Timeout exécution notebook (secondes)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "notebook":
            summary = run_notebook(
                feature_set=args.feature_set,
                use_fake=args.use_fake,
                notebook_path=Path(args.notebook),
                output_path=Path(args.output),
                timeout=args.timeout,
            )
        else:
            summary = run_pipeline(
                feature_set=args.feature_set,
                use_fake=args.use_fake,
            )
        _print_summary(summary)
        return 0 if summary.get("status") == "success" else 1
    except Exception:
        print("\n❌ NOTEBOOK 02 — ERREUR FATALE")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())