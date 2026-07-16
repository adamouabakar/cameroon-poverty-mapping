"""Tests configuration rapport ONG."""

from __future__ import annotations

from pathlib import Path

from src.reports.report_config import ReportOptions, load_report_config, t

ROOT = Path(__file__).resolve().parents[1]


def test_load_default_config():
    opts = load_report_config(project_root=ROOT)
    assert opts.language in ("fr", "en")
    assert opts.sections.get("cover", True)
    assert isinstance(opts.watchlist_rules, list)


def test_i18n_strings():
    assert "Rapport" in t("cover_title", "fr")
    assert "Report" in t("cover_title", "en")


def test_report_options_override():
    opts = ReportOptions(language="en", organization="Test NGO")
    assert opts.language == "en"
    assert opts.organization == "Test NGO"


def test_load_merged_partner_config():
    from src.reports.report_config import load_merged_config

    path = ROOT / "configs/partners/nord_humanitaire.yaml"
    opts = load_merged_config(path, project_root=ROOT)
    assert opts.focus_region == "Extrême-Nord"
    assert opts.sections.get("model_comparison") is False
    assert len(opts.watchlist_rules) == 2