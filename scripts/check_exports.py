"""Check that the Markdown exports (<page>.md, read by llms-full.txt, Ask AI and coding agents) keep every code line.

    python3 scripts/check_exports.py site/dist

For every docs page, the code lines inside fenced blocks of its source must all be in its exported <page>.md: an
export that drops `<AguiChat ... />` from a React example fails here. Exits with 1 on a loss, so CI fails.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "site" / "src" / "content" / "docs"
FENCE = re.compile(r"^[ \t]*(```|~~~)[^\n]*\n(.*?)^[ \t]*\1[ \t]*$", re.M | re.S)


def code_lines(text: str) -> list[str]:
    return [ln.strip() for m in FENCE.finditer(text) for ln in m.group(2).splitlines() if ln.strip()]


def export_of(dist: Path, src: Path) -> Path:
    rel = src.relative_to(DOCS).with_suffix("")
    rel = rel.parent if rel.name == "index" else rel
    return dist / "index.md" if str(rel) in ("", ".") else dist / f"{rel}.md"


def main() -> int:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "site/dist")
    lost: list[tuple[str, int, str]] = []
    pages = 0
    for src in sorted(DOCS.rglob("*.md*")):
        if "specifications" in src.parts:
            continue
        out = export_of(dist, src)
        if not out.is_file():
            continue
        pages += 1
        exported = set(code_lines(out.read_text(encoding="utf-8")))
        missing = [ln for ln in code_lines(src.read_text(encoding="utf-8")) if ln not in exported]
        if missing:
            lost.append((str(src.relative_to(DOCS)), len(missing), missing[0][:100]))
    print(f"{pages} pages, {len(lost)} with code lost in the export")
    for page, n, first in lost:
        print(f"  {page}: {n} line(s), e.g. {first}")
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
