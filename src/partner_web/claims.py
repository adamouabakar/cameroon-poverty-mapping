"""Load and validate configs/claims.yaml; resolve metrics from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from src.partner_web import EXIT_CLAIMS

REQUIRED_TOP = (
    "version",
    "country",
    "dhs_year",
    "contact_email",
    "banner_fr",
    "banner_en_one_liner",
    "layer_labels",
    "anti_targeting_fr",
    "metrics_keys",
    "wealth_units",
)

REQUIRED_LABELS = ("wealth", "priority", "uncertainty")
REQUIRED_METRIC_KEYS = ("r2", "spearman", "rmse", "n_clusters", "cv_strategy")


class ClaimsError(Exception):
    """Invalid claims document or metrics resolution."""

    def __init__(self, message: str, code: int = EXIT_CLAIMS):
        super().__init__(message)
        self.code = code


def load_claims(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ClaimsError(f"claims file missing: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ClaimsError("claims root must be a mapping")
    validate_claims(data)
    return data


def validate_claims(data: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_TOP if k not in data or data[k] in (None, "")]
    if missing:
        raise ClaimsError(f"claims missing required keys: {missing}")
    labels = data.get("layer_labels") or {}
    if not isinstance(labels, dict):
        raise ClaimsError("layer_labels must be a mapping")
    for k in REQUIRED_LABELS:
        if k not in labels or not str(labels[k]).strip():
            raise ClaimsError(f"layer_labels.{k} required")
    mk = data.get("metrics_keys") or {}
    if not isinstance(mk, dict):
        raise ClaimsError("metrics_keys must be a mapping")
    for k in REQUIRED_METRIC_KEYS:
        if k not in mk or not str(mk[k]).strip():
            raise ClaimsError(f"metrics_keys.{k} required")
    units = str(data.get("wealth_units", "")).lower()
    if units not in ("zscore", "raw"):
        raise ClaimsError("wealth_units must be zscore or raw")


def _dig(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise ClaimsError(f"metrics path not found: {dotted}")
        cur = cur[part]
    return cur


def resolve_metrics(claims: dict[str, Any], metrics_path: Path) -> dict[str, Any]:
    if not metrics_path.is_file():
        raise ClaimsError(f"metrics file missing: {metrics_path}")
    with metrics_path.open(encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[str, Any] = {}
    for key, dotted in claims["metrics_keys"].items():
        out[key] = _dig(raw, str(dotted))
    return out


def default_input_paths(project_root: Path, claims: dict[str, Any]) -> dict[str, Path]:
    """Resolve wealth (prefer z), priority, uncertainty, metrics."""
    overrides = claims.get("input_paths") or {}
    maps = project_root / "outputs" / "maps"
    reports = project_root / "outputs" / "reports"

    def ov(key: str, fallback: Path) -> Path:
        val = (overrides.get(key) or "").strip()
        if val:
            p = Path(val)
            return p if p.is_absolute() else project_root / p
        return fallback

    z = maps / "wealth_index_predicted_1km_model_z.tif"
    raw = maps / "wealth_index_predicted_1km_model.tif"
    wealth_default = z if z.is_file() else raw

    return {
        "wealth": ov("wealth", wealth_default),
        "priority": ov("priority", maps / "priority_index_1km.tif"),
        "uncertainty": ov("uncertainty", maps / "wealth_uncertainty_1km_model.tif"),
        "metrics": ov("metrics", reports / "real_model_results.json"),
    }
