"""Every configuration key the loader accepts is in the docs' configuration reference, and every documented key exists.

The keys come from `formguide.config.KEYS` (top-level key -> its sub-keys, or None when it has none); the docs side
is the "Every key" table of site/src/content/docs/reference/configuration.md (`model` / `models`, `memory.keep_turns`).
A new key fails here until the page has it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from formguide import config

PAGE = Path(__file__).resolve().parents[2] / "site" / "src" / "content" / "docs" / "reference" / "configuration.md"
CELL = re.compile(r"`([a-z_][a-z0-9_.]*)`")
KEYS = getattr(config, "KEYS", None)


def documented() -> dict[str, set[str]]:
    """Top-level key -> the sub-keys the table names with a dot (`memory.keep_turns`)."""
    table = PAGE.read_text(encoding="utf-8").split("\n## Every key", 1)[1].split("\n## ", 1)[0]
    keys: dict[str, set[str]] = {}
    for row in table.splitlines():
        if not row.startswith("| `"):
            continue
        for name in CELL.findall(row.split("|")[1]):
            top, _, sub = name.partition(".")
            keys.setdefault(top, set())
            if sub:
                keys[top].add(sub)
    return keys


@pytest.mark.xfail(KEYS is None, reason="formguide.config.KEYS is not there yet (Owner adds it)", strict=False)
def test_every_top_level_key_is_documented():
    assert KEYS is not None
    docs = set(documented())
    code = set(KEYS)
    assert code - docs == set(), f"accepted by the loader but not in reference/configuration.md: {sorted(code - docs)}"
    assert docs - code == set(), f"in reference/configuration.md but not accepted by the loader: {sorted(docs - code)}"


@pytest.mark.xfail(KEYS is None, reason="formguide.config.KEYS is not there yet (Owner adds it)", strict=False)
def test_documented_sub_keys_exist():
    assert KEYS is not None
    wrong = {f"{top}.{sub}" for top, subs in documented().items() for sub in subs
             if isinstance(KEYS.get(top), (set, frozenset, list, tuple, dict)) and sub not in KEYS[top]}
    assert wrong == set(), f"documented sub-keys the loader does not accept: {sorted(wrong)}"


def test_the_table_is_found():
    """The parser still reads the page (guards the two tests above against a renamed heading)."""
    keys = documented()
    assert {"model", "models", "memory", "knowledge"} <= set(keys) and "keep_turns" in keys["memory"]
