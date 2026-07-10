#!/usr/bin/env python
"""
Attend la fin du téléchargement (--force), puis finalise le ré-export VIIRS.

Usage :
  python scripts/wait_download_and_finalize_viirs.py
  python scripts/wait_download_and_finalize_viirs.py --poll-minutes 2
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
LOCK = PROJECT_ROOT / "data/processed/rasters/.download.lock"
REPORT = PROJECT_ROOT / "outputs/reports/viirs_reexport_status.json"
FORCE_START = datetime(2026, 7, 10, 1, 55, 11, tzinfo=timezone.utc).timestamp()


def _refreshed_tiles() -> int:
    tiles_dir = PROJECT_ROOT / "data/processed/rasters/tiles"
    if not tiles_dir.exists():
        return 0
    return sum(
        1 for t in tiles_dir.glob("tile_*.tif")
        if t.stat().st_mtime >= FORCE_START
    )


def _run(script: str, *args: str) -> int:
    cmd = [PYTHON, str(PROJECT_ROOT / "scripts" / script), *args]
    print(f"\n▶ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Attendre téléchargement puis finaliser VIIRS")
    p.add_argument("--poll-minutes", type=int, default=2)
    p.add_argument("--max-hours", type=float, default=8.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    poll_s = max(30, args.poll_minutes * 60)
    deadline = time.time() + args.max_hours * 3600

    print("▶ Surveillance téléchargement VIIRS (--force)…", flush=True)
    while time.time() < deadline:
        refreshed = _refreshed_tiles()
        locked = LOCK.exists()
        print(
            f"   [{datetime.now(timezone.utc).isoformat()}] "
            f"tuiles={refreshed}/96 lock={'oui' if locked else 'non'}",
            flush=True,
        )
        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "phase": "force_download",
            "tiles_refreshed": refreshed,
            "tiles_expected": 96,
            "lock_active": locked,
            "viirs_collection": "NASA/VIIRS/002/VNP46A2",
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

        if refreshed >= 96 and not locked:
            print("✅ Téléchargement terminé — finalisation VIIRS…", flush=True)
            return _run("finalize_viirs_reexport.py")

        time.sleep(poll_s)

    print("⏳ Timeout — relancez wait_download_and_finalize_viirs.py", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())