"""Tests packs livraison partenaires Phase 4."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.reports.partner_delivery import build_partner_delivery
from src.reports.partner_profile import load_partner_profile

ROOT = Path(__file__).resolve().parents[1]


def test_build_partner_delivery(tmp_path: Path):
    profile = load_partner_profile(ROOT, "generic_ngo")
    zip_path = build_partner_delivery(ROOT, profile, langs=("fr",), output_dir=tmp_path / "out")
    assert zip_path.is_file()
    assert zip_path.suffix == ".zip"

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert any("ngo_report_fr.pdf" in n for n in names)
        assert any("regional_stats.csv" in n for n in names)

    manifest = json.loads((tmp_path / "out" / "delivery_manifest.json").read_text(encoding="utf-8"))
    assert manifest["partner_id"] == "generic_ngo"
    assert manifest["phase"] == 4