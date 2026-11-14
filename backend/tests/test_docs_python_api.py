"""Every public method of FormGuide and Dushes, with its parameters, is in the docs' Python API reference, and every
documented one exists.

The code side is `inspect.signature` of the real classes (public = no leading underscore); the docs side is
site/src/content/docs/reference/python-api.mdx: the signatures of its ParamList entries and the method tables under
"## `FormGuide` methods" and "### `Dushes` methods", plus each entry's <Param> rows. A new method or parameter fails here
until the page has it.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

from formguide import FormGuide
from formguide.site import Dushes

PAGE = Path(__file__).resolve().parents[2] / "site" / "src" / "content" / "docs" / "reference" / "python-api.mdx"

# Public by name but used by the library itself, not by hosts; documented nowhere on purpose.
INTERNAL = {
    "FormGuide": {"actions_for", "deps", "layout", "tools_for"},
    "Dushes": {"classify", "doc_passages", "route"},
}

SIG = re.compile(r'signature="(?:\w+\.)?(\w+)\(([^"]*)\)"')
CELL = re.compile(r"`(?:async )?(\w+)\(([^`]*)\)`")
PARAM = re.compile(r'<Param name="([^"]+)"')


def code_methods(cls: type) -> dict[str, list[str]]:
    out = {}
    for name, fn in inspect.getmembers(cls, callable):
        if name.startswith("_") or name in INTERNAL[cls.__name__] or isinstance(inspect.getattr_static(cls, name), property):
            continue
        params = inspect.signature(fn).parameters.values()
        out[name] = [p.name for p in params if p.name != "self" and p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)]
    return out


def arg_names(args: str) -> list[str]:
    names = []
    for part in args.split(","):
        part = part.strip()
        if not part or part in ("*", "...") or part.startswith("*"):
            continue
        names.append(part.split("=", 1)[0].strip())
    return names


def block(text: str, heading: str) -> str:
    """The part of the page from `heading` to the next heading of the same level or higher."""
    level = heading.split(" ", 1)[0]
    start = text.index(heading) + len(heading)
    nxt = [m.start() for m in re.finditer(r"(?m)^#{1,%d} " % len(level), text[start:])]
    return text[start:start + nxt[0]] if nxt else text[start:]


def doc_methods(part: str) -> dict[str, list[str]]:
    """Method name -> the parameter names its signature shows; ParamList rows must match the signature."""
    out: dict[str, list[str]] = {}
    for m in SIG.finditer(part):
        name, sig = m.group(1), arg_names(m.group(2))
        body = part[m.end():part.find("</ParamList>", m.end())]
        rows = PARAM.findall(body)
        assert not rows or rows == sig, f"{name}: the Param rows {rows} differ from the signature {sig}"
        out[name] = sig
    for line in part.splitlines():
        if line.startswith("| `"):
            for name, args in CELL.findall(line.split("|")[1]):
                out[name] = arg_names(args)
    return out


def check(cls: type, heading: str) -> None:
    text = PAGE.read_text(encoding="utf-8")
    code, docs = code_methods(cls), doc_methods(block(text, heading))
    assert set(code) - set(docs) == set(), f"{cls.__name__} methods missing from python-api: {sorted(set(code) - set(docs))}"
    assert set(docs) - set(code) == set(), f"documented {cls.__name__} methods that do not exist: {sorted(set(docs) - set(code))}"
    wrong = {n: (docs[n], code[n]) for n in code if docs[n] != code[n]}
    assert wrong == {}, f"{cls.__name__} parameters differ (docs, code): {wrong}"


def test_formguide_methods_are_documented():
    check(FormGuide, "## `FormGuide` methods")


def test_dushes_methods_are_documented():
    check(Dushes, "### `Dushes` methods")


def test_internal_names_still_exist():
    """An internal helper that was renamed or removed leaves the list: keeps INTERNAL honest."""
    for cls in (FormGuide, Dushes):
        gone = {n for n in INTERNAL[cls.__name__] if not hasattr(cls, n)}
        assert gone == set(), f"{cls.__name__}: no longer exist, drop them from INTERNAL: {sorted(gone)}"
