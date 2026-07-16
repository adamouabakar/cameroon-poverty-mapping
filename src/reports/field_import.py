"""Import CSV validation terrain pour rapports ONG."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.partner_web.field_validation import FieldValidationError, load_sites_csv


def load_field_sites_for_report(csv_path: Path) -> pd.DataFrame:
    """Charge sites partenaires ; retourne DataFrame tabulaire."""
    if not csv_path.is_file():
        raise FieldValidationError(f"CSV terrain introuvable : {csv_path}")
    rows = load_sites_csv(csv_path)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "site_id": r.site_id,
                "region": r.region,
                "lat": r.lat,
                "lon": r.lon,
                "local_assessment": r.local_assessment,
                "predicted_wealth_bin": r.predicted_wealth_bin,
                "notes": (r.notes or "")[:80],
            }
            for r in rows
        ]
    )