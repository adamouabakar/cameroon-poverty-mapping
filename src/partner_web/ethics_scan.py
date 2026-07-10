"""Reject absolute host paths and sensitive DHS raw paths in generated site text."""

from __future__ import annotations

import re
from pathlib import Path

from src.partner_web import EXIT_PATH_LEAK

# Host path patterns (Windows drive, Unix home, DHS raw).
# Do NOT use bare [A-Za-z]:/ — it false-positives on https://
_PATTERNS = [
    re.compile(r"[A-Za-z]:\\"),  # C:\
    re.compile(r"(?<![a-zA-Z])[A-Za-z]:/(?!/)"),  # C:/ but not https://
    re.compile(r"/Users/[^/\s\"']+"),
    re.compile(r"/home/[^/\s\"']+"),
    re.compile(r"data/raw/dhs", re.IGNORECASE),
    re.compile(r"\\\\[A-Za-z]"),  # \\server\share
]


class EthicsError(Exception):
    def __init__(self, message: str, code: int = EXIT_PATH_LEAK):
        super().__init__(message)
        self.code = code


def scan_text(text: str, *, label: str = "content") -> None:
    for pat in _PATTERNS:
        m = pat.search(text)
        if m:
            raise EthicsError(f"path-leak in {label}: matched {m.group(0)!r}")


def scan_site_dir(site_dir: Path) -> None:
    if not site_dir.is_dir():
        return
    for path in site_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}:
            continue
        if path.suffix.lower() in {".js", ".css"} and "vendor" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # wealth_path in manifest may be relative posix — OK. Absolute host paths fail.
        scan_text(text, label=str(path.as_posix()))
