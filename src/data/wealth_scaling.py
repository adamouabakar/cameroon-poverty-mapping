"""Standardisation z-score de l'indice de richesse DHS (hv271 agrégé grappe)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class WealthScaler:
    mean: float
    std: float

    def fit(self, values: pd.Series | np.ndarray) -> WealthScaler:
        arr = np.asarray(values, dtype=float)
        self.mean = float(np.nanmean(arr))
        self.std = float(np.nanstd(arr))
        if self.std <= 0:
            raise ValueError("Écart-type nul — impossible de standardiser wealth_index.")
        return self

    def transform(self, values: pd.Series | np.ndarray) -> np.ndarray:
        arr = np.asarray(values, dtype=float)
        return (arr - self.mean) / self.std

    def inverse_transform(self, values: pd.Series | np.ndarray) -> np.ndarray:
        arr = np.asarray(values, dtype=float)
        return arr * self.std + self.mean

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> WealthScaler:
        return cls(mean=float(data["mean"]), std=float(data["std"]))


def save_scaler(scaler: WealthScaler, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "target": "wealth_index",
        "method": "zscore",
        **scaler.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_scaler(path: str | Path) -> WealthScaler:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return WealthScaler.from_dict(data)