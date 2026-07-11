"""Tests for field validation CSV + concordance helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.partner_web.field_validation import (
    FieldValidationError,
    load_sites_csv,
    validate_mvp_count,
    value_to_bin,
    write_reports,
    _concordance,
    SiteRow,
)

ROOT = Path(__file__).resolve().parents[1]


def test_value_to_bin():
    assert value_to_bin(0.0, 1.0, 2.0) == "bas"
    assert value_to_bin(1.5, 1.0, 2.0) == "moyen"
    assert value_to_bin(3.0, 1.0, 2.0) == "haut"


def test_load_csv_skips_example_and_validates(tmp_path: Path):
    p = tmp_path / "sites.csv"
    p.write_text(
        "site_id,region,lat,lon,predicted_wealth_bin,uncertainty_bin,"
        "local_assessment,notes,observer,date\n"
        "ex1,Littoral,,,moyen,moyen,similaire,,,\n"
        "s1,Littoral,4.05,9.70,bas,haut,plus pauvre,note,obs,2026-07-01\n"
        "s2,Littoral,4.06,9.71,moyen,moyen,similaire,,obs,2026-07-01\n"
        "s3,Littoral,4.07,9.72,haut,bas,plus aisé,,obs,2026-07-01\n"
        "s4,Littoral,4.08,9.73,bas,moyen,plus pauvre,,obs,2026-07-01\n"
        "s5,Littoral,4.09,9.74,moyen,haut,similaire,,obs,2026-07-01\n",
        encoding="utf-8",
    )
    rows = load_sites_csv(p)
    assert len(rows) == 5
    assert all(not r.site_id.startswith("ex") for r in rows)
    validate_mvp_count(rows, 5)


def test_mvp_count_fails():
    rows = [
        SiteRow("a", "R", 1.0, 2.0, "bas", "bas", "similaire", "", "o", "2026-01-01")
    ]
    with pytest.raises(FieldValidationError):
        validate_mvp_count(rows, 5)


def test_bad_local_assessment(tmp_path: Path):
    p = tmp_path / "bad.csv"
    p.write_text(
        "site_id,region,lat,lon,predicted_wealth_bin,uncertainty_bin,"
        "local_assessment,notes,observer,date\n"
        "s1,X,4,9,bas,bas,wrong,,o,2026-01-01\n",
        encoding="utf-8",
    )
    with pytest.raises(FieldValidationError):
        load_sites_csv(p)


def test_concordance_logic():
    r = SiteRow("a", "R", None, None, "bas", "bas", "plus pauvre", "", "o", "d")
    r.map_wealth_bin = "bas"
    assert _concordance(r) == "match"
    r.map_wealth_bin = "haut"
    assert _concordance(r) == "mismatch"


def test_write_reports(tmp_path: Path):
    rows = [
        SiteRow(
            f"s{i}",
            "Littoral",
            4.0 + i * 0.01,
            9.7,
            "moyen",
            "moyen",
            "similaire",
            "",
            "obs",
            "2026-07-01",
            map_wealth_bin="moyen",
            map_uncertainty_bin="moyen",
            concordance="match",
        )
        for i in range(5)
    ]
    md = tmp_path / "r.md"
    js = tmp_path / "r.json"
    write_reports(
        rows,
        md,
        js,
        partner="Test Partner",
        workshop_date="2026-07-01",
        workshop_minutes=60,
        region_focus="Littoral",
        map_url="https://example.com",
    )
    text = md.read_text(encoding="utf-8")
    assert "Test Partner" in text
    assert "Pas** de ciblage" in text or "Pas de ciblage" in text or "ciblage" in text
    assert js.is_file()
