"""Chargement et nettoyage des indicateurs INS/ECAM régionaux."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ins.regions import INS_CONTEXTUAL_COLUMNS, harmonize_region_name

DEFAULT_RAW_CSV = "data/reference/ins/ecam4_regional_indicators.csv"
RAW_FALLBACK_CSV = "data/raw/ins/ecam4_regional_indicators.csv"
DEFAULT_OUTPUT = "data/processed/ins_contextual_data.parquet"


def load_raw_ins_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Données INS introuvables : {path}")
    df = pd.read_csv(path)
    required = {"region_dhs", *INS_CONTEXTUAL_COLUMNS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes INS manquantes dans {path}: {sorted(missing)}")
    return df


def clean_ins_data(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie et déduplique par région DHS harmonisée."""
    out = df.copy()
    out["region_dhs"] = harmonize_region_name(out["region_dhs"])

    for col in INS_CONTEXTUAL_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = (
        out.sort_values("region_dhs")
        .drop_duplicates(subset=["region_dhs"], keep="first")
        .reset_index(drop=True)
    )

    if out[INS_CONTEXTUAL_COLUMNS].isna().any().any():
        bad = out[out[INS_CONTEXTUAL_COLUMNS].isna().any(axis=1)]
        raise ValueError(f"Valeurs manquantes INS après nettoyage :\n{bad}")

    ranges = {
        "poverty_rate_pct": (0, 100),
        "literacy_rate_15plus_pct": (0, 100),
        "electricity_access_pct": (0, 100),
        "primary_enrollment_pct": (0, 100),
    }
    for col, (lo, hi) in ranges.items():
        if ((out[col] < lo) | (out[col] > hi)).any():
            raise ValueError(f"{col} hors bornes [{lo}, {hi}]")

    out["source_survey"] = out.get("source_survey", "ECAM4").fillna("ECAM4")
    out["source_year"] = pd.to_numeric(out.get("source_year", 2014), errors="coerce").fillna(2014).astype(int)
    return out


def load_ins_contextual_data(
    raw_path: str | Path = DEFAULT_RAW_CSV,
    output_path: str | Path | None = DEFAULT_OUTPUT,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """
    Charge le CSV INS brut, nettoie et optionnellement écrit le parquet traité.
    """
    root = project_root or Path.cwd()
    raw = root / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)
    if not raw.exists() and raw_path == DEFAULT_RAW_CSV:
        raw = root / RAW_FALLBACK_CSV
    df = clean_ins_data(load_raw_ins_csv(raw))

    if output_path is not None:
        out = root / output_path if not Path(output_path).is_absolute() else Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)

    return df