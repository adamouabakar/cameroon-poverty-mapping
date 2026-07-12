"""Chargement indicateurs INS ECAM 5 (2022) — sources publiques."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.ins.load_ins import clean_ins_data, load_raw_ins_csv

DEFAULT_RAW_CSV = "data/reference/ins/ecam5_regional_indicators.csv"
DEFAULT_OUTPUT = "data/processed/ins_contextual_ecam5.parquet"

# Indicateurs nationaux ECAM5 (INS dépliant janvier 2024)
ECAM5_NATIONAL_2022: dict[str, float] = {
    "poverty_rate_pct": 37.7,
    "literacy_rate_15plus_pct": 75.3,
    "primary_enrollment_pct": 80.4,
    "urban_poverty_rate_pct": 21.6,
    "rural_poverty_rate_pct": 56.3,
}


def load_ecam5_contextual_data(
    raw_path: str | Path = DEFAULT_RAW_CSV,
    output_path: str | Path | None = DEFAULT_OUTPUT,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Charge ECAM5 régional, nettoie et écrit le parquet contextuel."""
    root = project_root or Path.cwd()
    raw = root / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)
    df = clean_ins_data(load_raw_ins_csv(raw))
    if output_path is not None:
        out = root / output_path if not Path(output_path).is_absolute() else Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)
    return df


def microdata_availability_report() -> dict[str, Any]:
    """Statut micro-données publiques vs partenariat INS."""
    return {
        "ecam5_unit_records": {
            "publicly_available": False,
            "access_route": "Partenariat formel INS Cameroun / demande micro-données ECAM5",
            "reference": "https://ins-cameroun.cm/statistique/ecam-5-principaux-indicateurs/",
        },
        "public_microdata_proxy": {
            "source": "DHS 2018 Cameroon cluster aggregates",
            "path": "data/processed/dhs_clusters_real.parquet",
            "n_clusters": 430,
            "note": "Wealth index par grappe — proxy micro pour validation et modélisation.",
        },
        "regional_tables": {
            "source": "data/reference/ins/ecam5_regional_indicators.csv",
            "poverty_published_regions": [
                "Extrême-Nord",
                "Nord-Ouest",
                "Nord",
                "Yaoundé",
                "Douala",
            ],
            "other_regions": "scaled_ecam4 or INS qualitative (above/below national mean)",
        },
        "methodology_change": (
            "ECAM5 nouvelle série EHCVM (2022) non comparable directement à ECAM4; "
            "validation sur rangs régionaux recommandée."
        ),
    }