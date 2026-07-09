#!/usr/bin/env python
"""Affiche le statut des tâches d'export GEE (Sprint 1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import ee

from src.features.gee.client import initialize_gee

WATCH_IDS = {
    "N6NPDMEZIKX7WX3PKVSU5O7C",
    "CZUNGBMUB5A25WTUKYUABRAC",
    "SB7JEBCKQPJTVGKF2IN2COJT",
}
WATCH_NAMES = {
    "cm_features_1km_v3",
    "cm_features_test_1km_v3",
}


def main() -> int:
    initialize_gee(project_id="cameroon-poverty-mapping", quiet=True)
    tasks = ee.batch.Task.list()
    matches = []
    for task in tasks:
        status = task.status()
        tid = status.get("id", "")
        desc = status.get("description", "")
        if tid in WATCH_IDS or desc in WATCH_NAMES:
            matches.append(
                {
                    "id": tid,
                    "state": status.get("state"),
                    "description": desc,
                    "creation_timestamp_ms": status.get("creation_timestamp_ms"),
                    "update_timestamp_ms": status.get("update_timestamp_ms"),
                    "error_message": status.get("error_message"),
                }
            )

    if not matches:
        print("Aucune tâche Sprint 1 trouvée dans les tâches récentes.")
        print("Vérifiez https://code.earthengine.google.com/tasks")
        return 0

    for row in matches:
        print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())