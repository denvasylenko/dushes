"""A tiny DSL used by the mock form backend to describe demo forms.

Not part of the agent. From one description it emits the JSX string (tags +
`name` only, occasionally text) and the initial props/state, like a real form
backend would.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------- DSL


@dataclass
class N:
    tag: str
    name: str
    label: str | None = None
    children: list["N | str"] = field(default_factory=list)
    props: dict[str, Any] = field(default_factory=dict)


def C(tag: str, name: str, label: str | None, *children: "N | str", **props: Any) -> N:
    return N(tag, name, label, list(children), props)


def F(tag: str, name: str, label: str, **props: Any) -> N:
    return N(tag, name, label, [], props)


def opts(*pairs: str) -> list[dict[str, str]]:
    """opts("id1:Name 1", "id2:Name 2") -> [{"id": ..., "name": ...}]."""
    out = []
    for p in pairs:
        i, n = p.split(":", 1)
        out.append({"id": i, "name": n})
    return out


# ---------------------------------------------------------------- emit

FIELD_DEFAULT = {"Checkbox": False, "Dropdown": None, "FileUpload": None}


def walk(n: N):
    yield n
    for ch in n.children:
        if isinstance(ch, N):
            yield from walk(ch)


def to_jsx(n: N, depth: int = 0) -> str:
    pad = "  " * depth
    if not n.children:
        return f'{pad}<{n.tag} name="{n.name}" />'
    inner = []
    for ch in n.children:
        inner.append(f"{pad}  {ch}" if isinstance(ch, str) else to_jsx(ch, depth + 1))
    return f'{pad}<{n.tag} name="{n.name}">\n' + "\n".join(inner) + f"\n{pad}</{n.tag}>"


def base_props(form: N) -> dict[str, dict[str, Any]]:
    """Initial props for every node: label, flags and per-field extras."""
    props: dict[str, dict[str, Any]] = {}
    for n in walk(form):
        p: dict[str, Any] = {"name": n.name, "visible": True}
        if n.label:
            p["label"] = n.label
        if n.tag not in ("Tabs", "Tab", "Accordion"):
            p.update({"disabled": False, "readonly": False, "required": False})
        p.update(n.props)
        props[n.name] = p
    return props


def initial_state(form: N) -> dict[str, Any]:
    """Empty state for every field."""
    st: dict[str, Any] = {}
    for n in walk(form):
        if n.tag in ("Tabs", "Tab", "Accordion"):
            continue
        st[n.name] = FIELD_DEFAULT.get(n.tag, "")
    return st

