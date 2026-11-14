"""The Form Lab's rule engine: one small helper per kind of backend rule, so a lab form is a description plus a
few lines of rules (the QA library of forms for the scenario evals; not part of the agent).

A lab form module (demo/mock_forms/lab/<name>.py) defines:

    FORM_ID = "clinic_intake"            # unique, snake_case
    FORM = C("Tabs", "main", None, ...)  # the DSL tree (demo/mock_forms/dsl.py)
    DOMAIN = {...} or None               # the inline domain pack; None: the form ships no pack
    PAGE = {"path": "/lab/clinic", "title": ..., "description": ..., "sections": [...]}   # its page on the Lab site
    SEQUENTIAL = True                    # optional: a tab unlocks when the tabs before it are complete
    def rules(h: H) -> None: ...         # optional: visibility, requirements, options, errors, computed values

`H` wraps the state and the props of one compute: read values with `h.val`, `h.id`, `h.num`, `h.date`,
change props with `h.show`, `h.require`, `h.disable`, `h.options`, `h.error`, and write computed (read-only)
values with `h.set`. Validators (`h.email`, `h.phone`, `h.iban`, ...) set the field's error only when it has a
value: an empty field is "missing", not "wrong".
"""
from __future__ import annotations

import copy
import re
from collections.abc import Callable, Iterable
from datetime import date
from typing import Any

from ..dsl import N, base_props, initial_state, to_jsx, walk

CONTAINERS = ("Tabs", "Tab", "Accordion")
EMPTY = (None, "", False, [], {})


class H:
    """One compute: the state `st` and the props `pr` (copied from the base, safe to change)."""

    def __init__(self, st: dict[str, Any], pr: dict[str, dict[str, Any]]):
        self.st, self.pr = st, pr

    # ------------------------------------------------------------ reading
    def val(self, n: str) -> Any:
        return self.st.get(n)

    def text(self, n: str) -> str:
        v = self.st.get(n)
        return "" if v is None else str(v).strip()

    def id(self, n: str) -> str | None:
        v = self.st.get(n)
        if isinstance(v, dict):
            return v.get("id")
        if isinstance(v, str) and v:   # a radio or a plain-string choice
            return v
        return None

    def ids(self, n: str) -> list[str]:
        """A multiselect: the ids picked."""
        v = self.st.get(n) or []
        if isinstance(v, dict):
            v = [v]
        return [x.get("id") if isinstance(x, dict) else str(x) for x in v] if isinstance(v, list) else []

    def on(self, n: str) -> bool:
        return self.st.get(n) is True

    def filled(self, *names: str) -> bool:
        return all(self.st.get(n) not in EMPTY for n in names)

    def num(self, n: str) -> float | None:
        try:
            return float(str(self.st.get(n)).replace(" ", "").replace(" ", "").replace(",", "."))
        except (TypeError, ValueError):
            return None

    def date(self, n: str) -> date | None:
        try:
            return date.fromisoformat(str(self.st.get(n) or "")[:10])
        except ValueError:
            return None

    def age(self, n: str, on: date | None = None) -> int | None:
        d, t = self.date(n), on or date.today()
        return None if d is None else t.year - d.year - ((t.month, t.day) < (d.month, d.day))

    # ------------------------------------------------------------ props
    def show(self, *names: str, when: bool = True) -> None:
        for n in names:
            self.pr[n]["visible"] = bool(when)

    def hide(self, *names: str, when: bool = True) -> None:
        self.show(*names, when=not when)

    def require(self, *names: str, when: bool = True) -> None:
        for n in names:
            self.pr[n]["required"] = bool(when)

    def disable(self, *names: str, when: bool = True) -> None:
        for n in names:
            self.pr[n]["disabled"] = bool(when)

    def readonly(self, *names: str, when: bool = True) -> None:
        for n in names:
            self.pr[n]["readonly"] = bool(when)

    def options(self, n: str, opts: list[dict[str, str]]) -> None:
        self.pr[n]["options"] = opts
        cur = self.id(n)
        if cur and isinstance(self.st.get(n), dict) and cur not in {o["id"] for o in opts}:
            self.st[n] = None   # the backend drops a choice that is no longer offered

    def error(self, n: str, msg: str) -> None:
        self.pr[n].setdefault("error", msg)

    def has_error(self, n: str) -> bool:
        return bool(self.pr.get(n, {}).get("error"))

    def set(self, n: str, v: Any) -> None:
        """A computed value: the backend writes it (the field is read-only in the description)."""
        self.st[n] = v

    def clear(self, *names: str) -> None:
        for n in names:
            self.st[n] = None if isinstance(self.st.get(n), dict) else ("" if not isinstance(self.st.get(n), bool) else False)

    # ------------------------------------------------------------ validators (only when the field has a value)
    def match(self, n: str, rx: str, msg: str) -> None:
        v = self.text(n)
        if v and not re.fullmatch(rx, v):
            self.error(n, msg)

    def email(self, n: str) -> None:
        self.match(n, r"[^@\s]+@[^@\s]+\.[^@\s]{2,}", "Enter a valid email address")

    def phone(self, n: str, msg: str = "Enter a valid phone number") -> None:
        v = self.text(n)
        if v and not re.fullmatch(r"\+?[\d\s\-().]{7,20}", v) or (v and len(re.sub(r"\D", "", v)) < 7):
            self.error(n, msg)

    def iban(self, n: str) -> None:
        v = re.sub(r"\s", "", self.text(n)).upper()
        if v and not iban_ok(v):
            self.error(n, "This IBAN is not valid (check the digits)")

    def number(self, n: str, lo: float | None = None, hi: float | None = None, msg: str | None = None,
               integer: bool = False) -> None:
        if not self.text(n):
            return
        x = self.num(n)
        if x is None or (integer and x != int(x)):
            self.error(n, "Enter a whole number" if integer else "Enter a number")
        elif (lo is not None and x < lo) or (hi is not None and x > hi):
            self.error(n, msg or f"Enter a value from {_fmt(lo)} to {_fmt(hi)}")

    def a_date(self, n: str, *, past: bool = False, future: bool = False, after: date | None = None,
               before: date | None = None, msg: str | None = None) -> None:
        if not self.text(n):
            return
        d, t = self.date(n), date.today()
        if d is None:
            self.error(n, "Enter a date")
        elif past and d > t:
            self.error(n, msg or "This date cannot be in the future")
        elif future and d < t:
            self.error(n, msg or "This date is in the past")
        elif after and d < after:
            self.error(n, msg or f"The date must be on or after {after.isoformat()}")
        elif before and d > before:
            self.error(n, msg or f"The date must be on or before {before.isoformat()}")

    def length(self, n: str, lo: int = 0, hi: int | None = None, msg: str | None = None) -> None:
        v = self.text(n)
        if v and (len(v) < lo or (hi is not None and len(v) > hi)):
            self.error(n, msg or (f"Use {lo} to {hi} characters" if hi else f"Use at least {lo} characters"))

    # ------------------------------------------------------------ repeating groups
    def repeat(self, count_field: str, groups: list[list[str]], required: Iterable[str] = ()) -> int:
        """Numbered groups (child_1_*, child_2_* ...): the first `count` are shown, the rest hidden.
        `required`: the name suffixes (after the number) that are required in a shown group."""
        x = self.num(count_field)
        k = max(0, min(len(groups), int(x))) if x is not None else 0
        req = tuple(required)
        for i, names in enumerate(groups):
            self.show(*names, when=i < k)
            for nm in names:
                if req and nm.endswith(req):
                    self.require(nm, when=i < k)
        return k


def iban_ok(v: str) -> bool:
    """The ISO 13616 check: country, check digits, mod 97."""
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", v):
        return False
    s = v[4:] + v[:4]
    return int("".join(str(int(c, 36)) for c in s)) % 97 == 1


def _fmt(x: float | None) -> str:
    return "" if x is None else (str(int(x)) if x == int(x) else str(x))


# ===================================================================== the compiled form


def _fields_of(n: N) -> list[N]:
    return [x for x in walk(n) if x.tag not in CONTAINERS]


def _complete(names: list[str], st: dict[str, Any], pr: dict[str, dict[str, Any]]) -> bool:
    for nm in names:
        p = pr[nm]
        if not p.get("visible", True) or p.get("disabled") or p.get("readonly"):
            continue
        if p.get("error") or (p.get("required") and st.get(nm) in EMPTY):
            return False
    return True


class LabForm:
    """A lab module compiled: the JSX the page renders and the backend's compute_config."""

    def __init__(self, form_id: str, form: N, rules: Callable[[H], None] | None = None, *,
                 sequential: bool = False, domain: dict[str, Any] | None = None, page: dict[str, Any] | None = None,
                 jsx: str | None = None):
        self.form_id, self.form, self.rules, self.sequential = form_id, form, rules, sequential
        self.domain, self.page = domain, page
        self.jsx = jsx or to_jsx(form)
        self.base_props, self.initial = base_props(form), initial_state(form)
        self.readonly = {n for n, p in self.base_props.items() if p.get("readonly")}
        # the top tabs in order, with the fields inside each one
        top = next((x for x in walk(form) if x.tag == "Tabs"), None)
        self.tabs = [(t.name, [f.name for f in _fields_of(t)]) for t in (top.children if top else []) if isinstance(t, N)]

    def compute_config(self, state: dict[str, Any] | None = None) -> dict[str, Any]:
        st = {**self.initial, **{k: v for k, v in (state or {}).items() if k in self.initial or k in self.base_props}}
        for n in self.readonly:   # read-only fields belong to the backend: a written value is not kept
            st[n] = self.initial.get(n, "")
        pr = copy.deepcopy(self.base_props)
        h = H(st, pr)
        if self.rules:
            self.rules(h)
        if self.sequential:
            ok = True
            for name, names in self.tabs:
                pr[name]["disabled"] = not ok
                ok = ok and _complete(names, st, pr)
        return {"props": pr, "state": st}
