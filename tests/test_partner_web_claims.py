"""Tests for claims loading and metrics resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.partner_web.claims import ClaimsError, load_claims, resolve_metrics, validate_claims

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
CLAIMS = ROOT / "configs" / "claims.yaml"


def test_load_claims_repo_default():
    data = load_claims(CLAIMS)
    assert data["country"] == "Cameroun"
    assert data["wealth_units"] in ("zscore", "raw")


def test_missing_key_raises(tmp_path: Path):
    bad = {"version": 1}
    p = tmp_path / "c.yaml"
    p.write_text(yaml.dump(bad), encoding="utf-8")
    with pytest.raises(ClaimsError) as ei:
        load_claims(p)
    assert ei.value.code == 5


def test_resolve_metrics_fixture():
    claims = load_claims(CLAIMS)
    # use fixture metrics keys (same schema)
    m = resolve_metrics(claims, FIX / "tiny_metrics.json")
    assert m["r2"] == 0.5
    assert m["n_clusters"] == 10


def test_resolve_metrics_missing_path():
    claims = load_claims(CLAIMS)
    with pytest.raises(ClaimsError):
        resolve_metrics(claims, FIX / "nope.json")
