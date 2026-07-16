"""Configuration et i18n rapports ONG."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("configs/ngo_report.yaml")

STRINGS: dict[str, dict[str, str]] = {
    "cover_title": {
        "fr": "Rapport ONG — Cameroon Poverty Mapping",
        "en": "NGO Report — Cameroon Poverty Mapping",
    },
    "ethics": {
        "fr": "Estimations exploratoires uniquement. Ne remplace pas l'INS. Pas de ciblage ménage/village.",
        "en": "Exploratory estimates only. Not official INS. No household/village targeting.",
    },
    "national_view": {"fr": "Vue nationale", "en": "National view"},
    "regional_stats": {
        "fr": "Statistiques par unité administrative DHS",
        "en": "Statistics by DHS administrative unit",
    },
    "ecam5_title": {
        "fr": "Comparaison ECAM 5 (2022) vs modèle",
        "en": "ECAM 5 (2022) vs model comparison",
    },
    "field_title": {
        "fr": "Validation terrain (sites partenaires)",
        "en": "Field validation (partner sites)",
    },
    "watchlist_title": {
        "fr": "Alertes régionales (seuils configurés)",
        "en": "Regional alerts (configured thresholds)",
    },
}


@dataclass
class ReportOptions:
    language: str = "fr"
    region: str = "Tout le Cameroun"
    focus_region: str = "Tout le Cameroun"
    partner_id: str = ""
    organization: str = "Cameroon Poverty Mapping"
    logo_path: Path | None = None
    contact_email: str = "abubakradamou@gmail.com"
    sections: dict[str, bool] = field(default_factory=lambda: {
        "cover": True,
        "maps": True,
        "regional_stats": True,
        "shap": True,
        "model_comparison": True,
        "ecam5_comparison": True,
        "field_validation": True,
        "watchlist_alerts": True,
    })
    field_csv: Path | None = None
    watchlist_rules: list[dict[str, Any]] = field(default_factory=list)


def t(key: str, lang: str) -> str:
    return STRINGS.get(key, {}).get(lang, STRINGS.get(key, {}).get("fr", key))


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if key == "inherits":
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def _options_from_raw(raw: dict[str, Any], root: Path) -> ReportOptions:
    org = raw.get("organization") or {}
    rep = raw.get("report") or {}
    logo = (org.get("logo_path") or "").strip()
    logo_path = (root / logo) if logo else None
    focus = str(rep.get("focus_region") or rep.get("default_region") or "Tout le Cameroun")

    default_sections = {
        "cover": True,
        "maps": True,
        "regional_stats": True,
        "shap": True,
        "model_comparison": True,
        "ecam5_comparison": True,
        "field_validation": True,
        "watchlist_alerts": True,
    }
    sections = {**default_sections, **(rep.get("sections") or {})}

    return ReportOptions(
        language=str(rep.get("default_language", "fr")).lower()[:2],
        focus_region=focus,
        partner_id=str(raw.get("partner_id") or ""),
        organization=str(org.get("name", "Cameroon Poverty Mapping")),
        logo_path=logo_path if logo_path and logo_path.is_file() else None,
        contact_email=str(org.get("contact_email", "abubakradamou@gmail.com")),
        sections=sections,
        field_csv=_resolve_field_csv(root, raw),
        watchlist_rules=list((raw.get("watchlist") or {}).get("alerts") or []),
    )


def load_report_config(path: Path | None = None, project_root: Path | None = None) -> ReportOptions:
    root = project_root or Path.cwd()
    cfg_path = root / (path or DEFAULT_CONFIG)
    if not cfg_path.is_file():
        return ReportOptions()

    with cfg_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return _options_from_raw(raw, root)


def load_merged_config(
    partner_path: Path,
    *,
    project_root: Path | None = None,
) -> ReportOptions:
    """Charge config partenaire en fusionnant avec inherits ou configs/ngo_report.yaml."""
    root = project_root or Path.cwd()
    partner_path = Path(partner_path)
    with partner_path.open(encoding="utf-8") as f:
        partner_raw = yaml.safe_load(f) or {}

    inherit_rel = partner_raw.get("inherits")
    if inherit_rel:
        base_path = root / str(inherit_rel)
        base_raw = yaml.safe_load(base_path.read_text(encoding="utf-8")) if base_path.is_file() else {}
    else:
        base_path = root / DEFAULT_CONFIG
        base_raw = yaml.safe_load(base_path.read_text(encoding="utf-8")) if base_path.is_file() else {}

    merged = _deep_merge_dict(base_raw, partner_raw)
    return _options_from_raw(merged, root)


def _resolve_field_csv(root: Path, raw: dict) -> Path | None:
    fv = raw.get("field_validation") or {}
    rel = (fv.get("default_csv") or "").strip()
    if not rel:
        return None
    p = root / rel
    return p if p.is_file() else None