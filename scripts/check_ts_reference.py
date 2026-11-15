"""Check that every field of the widget's public TypeScript types has a row in the docs reference, and the reverse.

    python3 scripts/check_ts_reference.py

The types are read from packages/agui-chat/src (the interface's own members); the rows are the <Param name="..."> entries
of the Parameter list with the given id on the reference page. A new option fails here until the page has it, and a
row for a field that no longer exists fails too. Exits with 1 on a difference, so CI fails.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "packages" / "agui-chat" / "src"
DOCS = ROOT / "site" / "src" / "content" / "docs"

# (source file, interface, reference page, the Parameter list's id)
TYPES = [
    ("rhf.ts", "UseFormguideOptions", "reference/form-hooks.mdx", "useformguideoptions"),
    ("rhf.ts", "UseFormguide", "reference/form-hooks.mdx", "what-it-returns"),
    ("formguide/schema.ts", "FormSchema", "reference/form-hooks.mdx", "formschema"),
    ("formguide/schema.ts", "SectionSchema", "reference/form-hooks.mdx", "sectionschema"),
    ("formguide/schema.ts", "FieldSchema", "reference/form-hooks.mdx", "fieldschema"),
]


def members(source: str, name: str) -> set[str]:
    """The member names of `export interface <name> { ... }` (one or many lines), at its own level only."""
    m = re.search(rf"export interface {name}\b[^{{]*{{", source)
    if not m:
        raise SystemExit(f"check_ts_reference: interface {name} not found")
    depth, i, body = 1, m.end(), []
    while depth and i < len(source):
        c = source[i]
        depth += c in "{(" and 1 or (c in "})" and -1 or 0)
        if depth == 1 or (depth == 0 and c != "}"):
            body.append(c)
        i += 1
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", "".join(body), flags=re.S)
    return set(re.findall(r"(?:^|[;\n])\s*(\w+)\??\s*:", text))


def rows(page: str, list_id: str) -> set[str]:
    m = re.search(rf'<ParamList\b[^>]*\bid="{list_id}"[^>]*>(.*?)</ParamList>', page, re.S)
    if not m:
        raise SystemExit(f'check_ts_reference: no Parameter list with id="{list_id}"')
    return set(re.findall(r'<Param name="([^"]+)"', m.group(1)))


def main() -> int:
    bad = 0
    for file, name, page, list_id in TYPES:
        code = members((SRC / file).read_text(encoding="utf-8"), name)
        docs = rows((DOCS / page).read_text(encoding="utf-8"), list_id)
        if code != docs:
            bad += 1
            print(f"{name} ({page}#{list_id}): not documented {sorted(code - docs)}, no longer exists {sorted(docs - code)}")
    print(f"{len(TYPES)} types, {bad} out of step with the reference")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
