"""Tests profils partenaires Phase 4."""

from __future__ import annotations

from pathlib import Path

from src.reports.partner_profile import list_partner_profiles, load_partner_profile

ROOT = Path(__file__).resolve().parents[1]


def test_list_partner_profiles():
    profiles = list_partner_profiles(ROOT)
    assert len(profiles) >= 3
    ids = {p.partner_id for p in profiles}
    assert "generic_ngo" in ids
    assert "nord_humanitaire" in ids


def test_load_nord_humanitaire():
    p = load_partner_profile(ROOT, "nord_humanitaire")
    assert p.focus_region == "Extrême-Nord"
    assert p.options.organization == "Alliance humanitaire Nord Cameroun"
    assert p.options.sections.get("model_comparison") is False


def test_inherits_base_watchlist_for_generic():
    p = load_partner_profile(ROOT, "generic_ngo")
    assert p.focus_region == "Tout le Cameroun"
    assert len(p.options.watchlist_rules) >= 1