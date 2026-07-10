#!/usr/bin/env python
"""
Migration VIIRS : NOAA/001 → NASA/002.

Valide le nouveau composite sur l'AOI test Yaoundé et produit un rapport.

Usage :
  python scripts/migrate_viirs.py
  python scripts/migrate_viirs.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORT_PATH = PROJECT_ROOT / "outputs/reports/viirs_migration.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Valider migration VIIRS NASA/002")
    p.add_argument("--dry-run", action="store_true", help="Vérifier config uniquement")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    from src.features.gee.config import load_gee_config

    config = load_gee_config()
    viirs = config["viirs"]

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "config_ok",
        "collection": viirs["collection"],
        "band": viirs["band"],
        "quality_clear_values": viirs.get("quality_clear_values"),
        "composite_method": viirs.get("composite_method", "median"),
        "period": {
            "start": config["temporal"]["viirs_start"],
            "end": config["temporal"]["viirs_end"],
        },
    }

    if args.dry_run:
        print("✅ Configuration VIIRS NASA/002 valide (dry-run)")
        for k, v in report.items():
            if k != "timestamp_utc":
                print(f"  {k}: {v}")
        return 0

    from src.features.gee.client import initialize_from_config
    from src.features.gee.smoke_test import run_yaounde_smoke_test

    print("▶ Initialisation GEE + smoke test Yaoundé…")
    initialize_from_config()
    smoke = run_yaounde_smoke_test(config)
    viirs_sample = smoke["samples"].get("viirs", {}).get("night_lights")

    report["status"] = "smoke_ok" if viirs_sample is not None else "smoke_masked"
    report["smoke_test"] = smoke
    report["next_steps"] = [
        "Ré-extraire features grappes : python scripts/extract_gee_features.py --mode clusters --feature-set v3",
        "Ré-exporter raster national : python scripts/extract_gee_features.py --mode national --feature-set v3 --destination drive",
        "Re-télécharger tuiles + inférence : python scripts/finalize_national_coverage.py",
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"✅ Migration VIIRS validée — night_lights @ Yaoundé : {viirs_sample}")
    print(f"   Rapport : {REPORT_PATH}")
    if report["status"] != "smoke_ok":
        print("⚠️  Échantillon VIIRS masqué — vérifier qualité / période.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())