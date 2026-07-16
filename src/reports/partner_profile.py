"""Profils partenaires ONG — Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.reports.report_config import ReportOptions, load_merged_config

PARTNERS_DIR = Path("configs/partners")


@dataclass
class PartnerProfile:
    partner_id: str
    display_name: str
    focus_region: str
    config_path: Path
    options: ReportOptions


def list_partner_profiles(project_root: Path) -> list[PartnerProfile]:
    """Liste les profils YAML dans configs/partners/."""
    root = Path(project_root)
    partners_dir = root / PARTNERS_DIR
    if not partners_dir.is_dir():
        return []

    profiles: list[PartnerProfile] = []
    for path in sorted(partners_dir.glob("*.yaml")):
        try:
            profiles.append(load_partner_profile(root, path.stem))
        except Exception:
            continue
    return profiles


def load_partner_profile(project_root: Path, partner_id: str) -> PartnerProfile:
    """Charge un profil par identifiant (nom de fichier sans extension)."""
    root = Path(project_root)
    path = root / PARTNERS_DIR / f"{partner_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Profil partenaire introuvable : {partner_id}")

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    opts = load_merged_config(path, project_root=root)
    display = str(raw.get("display_name") or opts.organization or partner_id)
    focus = str(raw.get("report", {}).get("focus_region") or opts.focus_region)

    return PartnerProfile(
        partner_id=str(raw.get("partner_id") or partner_id),
        display_name=display,
        focus_region=focus,
        config_path=path,
        options=opts,
    )