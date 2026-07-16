"""Pytest configuration — backend matplotlib headless."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")