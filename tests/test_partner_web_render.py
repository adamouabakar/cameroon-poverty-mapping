"""Warp / PNG / empty uncertainty tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.partner_web.render import (
    RenderError,
    array_to_png,
    build_layer_stack,
    is_empty_layer,
    load_master_wealth,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"


def test_warp_mismatched_grids_align():
    stack = build_layer_stack(
        FIX / "tiny_wealth.tif",
        FIX / "tiny_priority.tif",
        FIX / "tiny_uncertainty.tif",
        max_edge=64,
    )
    assert stack.wealth.shape == stack.priority.shape == stack.uncertainty.shape
    assert "west" in stack.bounds_wgs84
    assert stack.bounds_wgs84["east"] > stack.bounds_wgs84["west"]


def test_empty_uncertainty_exit_code():
    with pytest.raises(RenderError) as ei:
        build_layer_stack(
            FIX / "tiny_wealth.tif",
            FIX / "tiny_priority.tif",
            FIX / "tiny_uncertainty_empty.tif",
        )
    assert ei.value.code == 3


def test_missing_priority_exit_2():
    with pytest.raises(RenderError) as ei:
        build_layer_stack(
            FIX / "tiny_wealth.tif",
            FIX / "does_not_exist.tif",
            FIX / "tiny_uncertainty.tif",
        )
    assert ei.value.code == 2


def test_array_to_png_and_bounds(tmp_path: Path):
    stack = build_layer_stack(
        FIX / "tiny_wealth.tif",
        FIX / "tiny_priority.tif",
        FIX / "tiny_uncertainty.tif",
    )
    png = tmp_path / "w.png"
    array_to_png(stack.wealth, png)
    assert png.is_file() and png.stat().st_size > 100
    assert not is_empty_layer(stack.uncertainty)


def test_load_master_max_edge():
    arr, transform, crs = load_master_wealth(FIX / "tiny_wealth.tif", max_edge=16)
    assert max(arr.shape) <= 16
    assert crs is not None
