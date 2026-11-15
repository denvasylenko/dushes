"""Check that the Markdown exports (<page>.md, read by llms-full.txt, Ask AI and coding agents) keep every code line.

    python3 scripts/check_exports.py site/dist

For every docs page, the code lines inside fenced blocks of its source must all be in its exported <page>.md: an
export that drops `<AguiChat ... />` from a React example fails here. A page that shows a recipe's files
(`<RecipeFiles name="x" />`) must export every line of backend/demo/recipes/x/. And no component tag may be left in an
export outside code (a `<Disclosure ...>` the exporter does not know). Exits with 1 on a loss, so CI fails.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "site" / "src" / "content" / "docs"
RECIPES = ROOT / "backend" / "demo" / "recipes"
RECIPE = re.compile(r'<RecipeFiles\s+name="([^"]+)"')
TAG = re.compile(r"</?[A-Z][A-Za-z]+(?=[\s>/])")   # a component left in the text, e.g. <Disclosure summary=...>
FENCE = re.compile(r"^[ \t]*(```|~~~)[^\n]*\n(.*?)^[ \t]*\1[ \t]*$", re.M | re.S)


def code_lines(text: str) -> list[str]:
    return [ln.strip() for m in FENCE.finditer(text) for ln in m.group(2).splitlines() if ln.strip()]


def recipe_lines(name: str) -> list[str]:
    files = [f for f in sorted((RECIPES / name).rglob("*")) if f.is_file() and f.suffix in (".yaml", ".md", ".py")
             and "__pycache__" not in f.parts]
    return [ln.strip() for f in files for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]


def stray_tags(text: str) -> list[str]:
    """Component tags outside fenced code and inline code."""
    body = re.sub(r"\A(?:#[^\n]*\n+)?>[^\n]*\n", "", text)   # the page's one-line description is prose, e.g. "<AguiChat> is ..."
    prose = re.sub(r"`[^`\n]*`", "", FENCE.sub("", body))
    cut = ['a tag cut at ">" inside an attribute'] if re.search(r'" id="[\w-]+">', prose) else []
    return TAG.findall(prose) + cut


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
        text = out.read_text(encoding="utf-8")
        exported = set(code_lines(text))
        source = src.read_text(encoding="utf-8")
        wanted = code_lines(source) + [ln for name in RECIPE.findall(source) for ln in recipe_lines(name)]
        missing = [ln for ln in wanted if ln not in exported]
        missing += [f"left in the text: {t}" for t in dict.fromkeys(stray_tags(text))]
        if missing:
            lost.append((str(src.relative_to(DOCS)), len(missing), missing[0][:100]))
    print(f"{pages} pages, {len(lost)} with code lost in the export")
    for page, n, first in lost:
        print(f"  {page}: {n} line(s), e.g. {first}")
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
