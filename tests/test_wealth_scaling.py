import numpy as np
import pandas as pd
import pytest

from src.data.wealth_scaling import WealthScaler, load_scaler, save_scaler


def test_zscore_roundtrip(tmp_path):
    values = pd.Series([100.0, 200.0, 300.0, 400.0])
    scaler = WealthScaler(mean=0.0, std=1.0).fit(values)
    z = scaler.transform(values)
    restored = scaler.inverse_transform(z)
    np.testing.assert_allclose(restored, values.values, rtol=1e-6)


def test_save_load_scaler(tmp_path):
    scaler = WealthScaler(mean=10.0, std=2.5)
    path = tmp_path / "wealth_scaler.json"
    save_scaler(scaler, path)
    loaded = load_scaler(path)
    assert loaded.mean == pytest.approx(10.0)
    assert loaded.std == pytest.approx(2.5)