"""Harmonisation des noms de régions DHS / INS / ECAM."""

from __future__ import annotations

import pandas as pd

# Aligné sur src/data/prepare_real_dhs.py
DHS_REGION_NORMALIZE: dict[str, str] = {
    "EXTREME-NORD": "Extrême-Nord",
    "NORD-OUEST": "Nord-Ouest",
    "SUD-OUEST": "Sud-Ouest",
    "ADAMAOUA": "Adamaoua",
    "CENTRE": "Centre",
    "EST": "Est",
    "LITTORAL": "Littoral",
    "NORD": "Nord",
    "OUEST": "Ouest",
    "SUD": "Sud",
    "DOUALA": "Douala",
    "YAOUNDE": "Yaoundé",
}

INS_CONTEXTUAL_COLUMNS = [
    "poverty_rate_pct",
    "literacy_rate_15plus_pct",
    "electricity_access_pct",
    "primary_enrollment_pct",
]

INS_FEATURE_COLUMNS_V4 = [
    "ins_poverty_rate_pct",
    "ins_literacy_rate_15plus_pct",
    "ins_electricity_access_pct",
    "ins_primary_enrollment_pct",
]


def harmonize_region_name(series: pd.Series) -> pd.Series:
    """Uniformise les libellés de région (DHS → format projet)."""
    upper = series.astype(str).str.strip().str.upper()
    mapped = upper.map(DHS_REGION_NORMALIZE)
    return mapped.fillna(series.astype(str).str.strip())


def map_dhs_to_ins(region: str) -> str:
    """Retourne la clé région utilisée pour joindre les données INS."""
    return harmonize_region_name(pd.Series([region])).iloc[0]