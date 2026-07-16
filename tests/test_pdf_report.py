"""Tests générateur PDF ONG."""

from __future__ import annotations

from pathlib import Path

from src.reports.pdf_report import generate_ngo_pdf_report
from src.reports.report_config import ReportOptions

ROOT = Path(__file__).resolve().parents[1]


def test_generate_pdf_bytes():
    data = generate_ngo_pdf_report(ROOT, region="Tout le Cameroun")
    assert isinstance(data, bytes)
    assert data[:4] == b"%PDF"


def test_generate_pdf_to_file(tmp_path: Path):
    out = tmp_path / "test_report.pdf"
    data = generate_ngo_pdf_report(ROOT, region="Nord", output_path=out)
    assert out.is_file()
    assert len(data) > 10_000


def test_generate_pdf_english():
    opts = ReportOptions(language="en", sections={"maps": False, "shap": False})
    data = generate_ngo_pdf_report(ROOT, options=opts)
    assert data[:4] == b"%PDF"
    assert len(data) > 5000