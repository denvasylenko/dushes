"""Fail if any tracked text file contains Cyrillic characters (the repository is English-only).

    python3 scripts/check_english.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "data", "runs", "__pycache__", ".pytest_cache", ".astro",
             ".deploy"}   # .deploy: local, git-excluded deploy files and their build output
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ico", ".lock"}
CYRILLIC = re.compile(r"[\u0400-\u052f]")  # Cyrillic + Cyrillic Supplement


def main() -> int:
    bad = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if CYRILLIC.search(line):
                print(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:120]}")
                bad += 1
    if bad:
        print(f"\n{bad} line(s) with Cyrillic text. The repository is English-only.")
        return 1
    print("OK: no Cyrillic text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
