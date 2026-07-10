#!/usr/bin/env python
"""
Attend la fin d'un export GEE Drive, puis télécharge et finalise la couverture nationale.

Usage :
  python scripts/wait_gee_export_and_finalize.py --task-id 37BCJG6Z5RLRIYHZFHY32OZA
  python scripts/wait_gee_export_and_finalize.py --poll-minutes 5
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PYTHON = sys.executable
REPORT = PROJECT_ROOT / "outputs/reports/viirs_reexport_status.json"
EXPORT_REPORT = PROJECT_ROOT / "outputs/reports/gee_national_export.json"


def _load_task_id() -> str:
    if EXPORT_REPORT.exists():
        data = json.loads(EXPORT_REPORT.read_text(encoding="utf-8"))
        if data.get("task_id"):
            return data["task_id"]
    raise FileNotFoundError("task_id introuvable — lancez extract_gee_features.py --mode national")


def _task_status(task_id: str) -> dict:
    import ee
    from src.features.gee.client import initialize_gee

    initialize_gee(project_id="cameroon-poverty-mapping", quiet=True)
    for task in ee.batch.Task.list():
        status = task.status()
        if status.get("id") == task_id:
            return status
    return {"id": task_id, "state": "UNKNOWN"}


def _run(script: str, *args: str) -> int:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n▶ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Attendre export GEE puis finaliser")
    p.add_argument("--task-id", default=None)
    p.add_argument("--poll-minutes", type=int, default=5)
    p.add_argument("--max-hours", type=float, default=6.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    task_id = args.task_id or _load_task_id()
    poll_s = max(60, args.poll_minutes * 60)
    deadline = time.time() + args.max_hours * 3600

    print(f"▶ Surveillance export GEE : {task_id}")
    while time.time() < deadline:
        status = _task_status(task_id)
        state = status.get("state", "UNKNOWN")
        print(f"   [{datetime.now(timezone.utc).isoformat()}] state={state}")

        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "state": state,
            "viirs_collection": "NASA/VIIRS/002/VNP46A2",
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

        if state == "COMPLETED":
            print("✅ Export GEE terminé — téléchargement national…")
            code = _run(
                "download_gee_raster_local.py",
                "--mode", "national", "--tiles", "--force",
            )
            if code != 0:
                return code
            return _run("finalize_national_coverage.py")

        if state in ("FAILED", "CANCELLED"):
            print(f"❌ Export GEE {state}: {status.get('error_message', '')}")
            return 1

        time.sleep(poll_s)

    print("⏳ Timeout — relancez wait_gee_export_and_finalize.py plus tard.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())