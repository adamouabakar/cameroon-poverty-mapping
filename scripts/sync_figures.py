#!/usr/bin/env python
"""Copie les aperçus cartes vers figures/ pour le README."""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAPS = PROJECT_ROOT / "outputs/maps"
FIGURES = PROJECT_ROOT / "figures"

COPIES = {
    "wealth_index_predicted_1km_model_v4.png": "wealth_national_v4_preview.png",
    "priority_index_1km_v4.png": "priority_v4_preview.png",
    "wealth_uncertainty_1km_model_v4.png": "uncertainty_v4_preview.png",
    "ins_external_validation_scatter.png": "ins_validation_scatter.png",
}


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for src_name, dst_name in COPIES.items():
        src = MAPS / src_name
        dst = FIGURES / dst_name
        if not src.exists():
            print(f"⚠️  Absent : {src}")
            continue
        shutil.copy2(src, dst)
        print(f"✓ {dst_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())