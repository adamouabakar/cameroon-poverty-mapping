"""CLI e2e, ethics scan, HTML/zip contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from src.partner_web.ethics_scan import EthicsError, scan_site_dir, scan_text

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
CLI = ROOT / "scripts" / "build_partner_web.py"


def test_path_leak_scan_detects_windows_path():
    with pytest.raises(EthicsError) as ei:
        scan_text(r'path C:\Users\me\secret', label="t")
    assert ei.value.code == 7


def test_path_leak_scan_detects_dhs_raw():
    with pytest.raises(EthicsError):
        scan_text("see data/raw/dhs/file.dta", label="t")


def test_clean_site_passes(tmp_path: Path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html>ok relative assets/wealth.png</html>", encoding="utf-8")
    scan_site_dir(site)


def test_cli_e2e_fixtures(tmp_path: Path):
    site = tmp_path / "site"
    pack = tmp_path / "pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--fixtures",
            "--out-site",
            str(site),
            "--out-pack",
            str(pack),
            "--claims",
            str(ROOT / "configs" / "claims.yaml"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (site / "index.html").is_file()
    assert (site / "assets" / "wealth.png").is_file()
    assert (site / "vendor" / "leaflet" / "leaflet.js").is_file()
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "unpkg.com" not in html and "cdnjs" not in html
    assert "mailto:" in html
    assert "vendor/leaflet/leaflet.js" in html
    assert (site / "build_manifest.json").is_file()
    man = json.loads((site / "build_manifest.json").read_text(encoding="utf-8"))
    assert man["absolute_path_scan"] == "pass"
    assert (pack / "brief_fr.md").is_file()
    assert (pack / "brief_en.md").is_file()
    en = (pack / "brief_en.md").read_text(encoding="utf-8")
    assert "R² OOF" in en or "R2 OOF" in en or "OOF" in en
    assert "0.5" in en  # fixture metrics r2
    assert "targeting" in en.lower() or "household" in en.lower()
    assert "http" in en  # map link placeholder
    assert (pack / "offline_bundle.zip").is_file()
    with zipfile.ZipFile(pack / "offline_bundle.zip") as zf:
        names = zf.namelist()
        assert any(n.endswith("index.html") for n in names)
        assert any("leaflet.js" in n for n in names)


def test_cli_empty_uncertainty_exit_3(tmp_path: Path):
    site = tmp_path / "site"
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--wealth",
            str(FIX / "tiny_wealth.tif"),
            "--priority",
            str(FIX / "tiny_priority.tif"),
            "--uncertainty",
            str(FIX / "tiny_uncertainty_empty.tif"),
            "--metrics",
            str(FIX / "tiny_metrics.json"),
            "--out-site",
            str(site),
            "--out-pack",
            str(tmp_path / "pack"),
            "--skip-pack",
            "--claims",
            str(ROOT / "configs" / "claims.yaml"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 3, proc.stderr
