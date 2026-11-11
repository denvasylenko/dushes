"""Config overlay: applies a fresh config (props + state) on top of the static layout.

- effective flags (visibility / disabled state are inherited from containers);
- a snapshot used to compare configs between messages;
- a semantic diff (what the user changed and how the form reacted);
- DepStore: dependencies inferred from observations (the config does not declare them).
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layout import LayoutIndex, Node


# ===================================================================== effective view


@dataclass
class Eff:
    node: Node
    props: dict[str, Any]
    value: Any
    visible: bool          # including ancestors
    disabled: bool         # including ancestors
    own_visible: bool
    own_disabled: bool
    missing: bool          # name exists in JSX but not in config

    @property
    def name(self) -> str:
        return self.node.name

    @property
    def label(self) -> str | None:
        return self.props.get("label")

    @property
    def readonly(self) -> bool:
        return bool(self.props.get("readonly"))

    @property
    def required(self) -> bool:
        return bool(self.props.get("required"))

    @property
    def error(self) -> str | None:
        return self.props.get("error") or None

    @property
    def options(self) -> list[dict] | None:
        o = self.props.get("options")
        return o if isinstance(o, list) else None

    @property
    def editable(self) -> bool:
        return self.visible and not self.disabled and not self.readonly

    @property
    def filled(self) -> bool:
        v = self.value
        if self.node.role == "bool":
            return v is True
        if isinstance(v, str):
            return bool(v.strip())
        return v is not None

    @property
    def needs_input(self) -> bool:
        """Required, editable and still empty."""
        return self.editable and self.required and not self.filled

    @property
    def invalid_value(self) -> bool:
        if self.node.role != "select" or not isinstance(self.value, dict):
            return False
        ids = {o.get("id") for o in self.options or []}
        return self.value.get("id") not in ids

    def options_sig(self) -> str:
        if self.options is None:
            return ""
        return hashlib.md5(json.dumps(self.options, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]


class Overlay:
    def __init__(self, layout: LayoutIndex, config: dict[str, Any], pii: set[str] | None = None):
        self.layout = layout
        self.pii = pii or set()
        props = config.get("props") or {}
        state = config.get("state") or {}
        self.unknown_in_config = sorted(set(props) - set(layout.nodes))
        self.eff: dict[str, Eff] = {}
        for name in layout.order:  # preorder: a parent always comes before its children
            n = layout.nodes[name]
            p = props.get(name)
            missing = p is None and n.is_field
            p = p or {}
            own_v = bool(p.get("visible", True)) and not missing
            own_d = bool(p.get("disabled", False))
            par = self.eff.get(n.parent) if n.parent else None
            self.eff[name] = Eff(
                node=n, props=p, value=state.get(name),
                own_visible=own_v, own_disabled=own_d, missing=missing,
                visible=own_v and (par.visible if par else True),
                disabled=own_d or (par.disabled if par else False),
            )

    def __getitem__(self, name: str) -> Eff:
        return self.eff[name]

    def get(self, name: str) -> Eff | None:
        return self.eff.get(name)

    # -------------------------------------------------------------- helpers
    def hidden_root(self, name: str) -> Eff | None:
        """The topmost hidden node among `name` and its ancestors: the reason it is hidden."""
        for a in self.layout.ancestors(name) + [self.layout.nodes[name]]:
            e = self.eff[a.name]
            if not e.own_visible:
                return e
        return None

    def disabled_root(self, name: str) -> Eff | None:
        for a in self.layout.ancestors(name) + [self.layout.nodes[name]]:
            e = self.eff[a.name]
            if e.own_disabled:
                return e
        return None

    def blockers(self, name: str, per_group: int = 3) -> list[str]:
        """A guess at why a section is disabled: required empty fields that come
        earlier in the form (typical "step" logic). Grouped by step (top-level
        container), nearest step first."""
        pos = {n: i for i, n in enumerate(self.layout.order)}
        groups: dict[str, list[str]] = {}
        for n in self.layout.order[:pos[name]]:
            e = self.eff[n]
            if e.node.is_field and e.needs_input:
                anc = [a for a in self.layout.ancestors(n) if a.role != "tabs"]
                step = anc[0].name if anc else "?"
                groups.setdefault(step, []).append(n)
        out = []
        for step, fields in reversed(groups.items()):
            lbl = self.eff[step].label if step in self.eff else step
            more = f" +{len(fields) - per_group}" if len(fields) > per_group else ""
            out.append(f"\"{lbl}\": {', '.join(fields[:per_group])}{more}")
        return out

    def required_inside(self, container: str) -> int:
        """Number of required visible fields inside, including disabled ones."""
        return sum(1 for d in self.layout.descendants(container)
                   if d.is_field and self.eff[d.name].visible and self.eff[d.name].required)

    def progress(self, container: str) -> tuple[int, int]:
        """(filled, total) over required editable fields inside the container."""
        done = total = 0
        for d in self.layout.descendants(container):
            e = self.eff[d.name]
            if d.is_field and e.editable and e.required:
                total += 1
                done += e.filled
        return done, total

    def display_value(self, e: Eff, limit: int = 40) -> str:
        v = e.value
        if not e.filled:
            return "∅"
        if e.name in self.pii:
            return "<filled>"
        if e.node.role == "bool":
            return "yes"
        if e.node.role == "file":
            return f"file \"{v.get('name', 'uploaded')}\"" if isinstance(v, dict) else "uploaded"
        if isinstance(v, dict):
            return f"\"{v.get('name')}\" (id={v.get('id')})"
        s = str(v)
        return f'"{s[:limit]}…"' if len(s) > limit else f'"{s}"'

    def snapshot(self) -> dict[str, list]:
        snap = {}
        for name, e in self.eff.items():
            if e.node.role == "static_text":
                continue
            snap[name] = [self.display_value(e), e.visible, e.disabled, e.readonly, e.required,
                          e.options_sig(), len(e.options or []), e.error, e.invalid_value,
                          _trigger_value(e)]
        return snap


def _trigger_value(e: Eff) -> str:
    """A field value as a "condition" for the dependency map: "<id>|<display name>"."""
    v = e.value
    if e.node.role == "select":
        return f"{v.get('id')}|{v.get('name')}" if isinstance(v, dict) else "∅|not selected"
    if e.node.role == "bool":
        return "true|checked" if v is True else "false|unchecked"
    return "*|filled" if e.filled else "∅|empty"


# ===================================================================== diff

S_DISP, S_VIS, S_DIS, S_RO, S_REQ, S_OSIG, S_OCNT, S_ERR, S_INV, S_TRIG = range(10)


@dataclass
class Diff:
    user_values: list[tuple[str, str, str]] = field(default_factory=list)
    agent_values: list[tuple[str, str, str]] = field(default_factory=list)
    derived_values: list[tuple[str, str, str]] = field(default_factory=list)
    appeared: list[str] = field(default_factory=list)
    disappeared: list[str] = field(default_factory=list)
    enabled: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)
    required_on: list[str] = field(default_factory=list)
    required_off: list[str] = field(default_factory=list)
    options: list[tuple[str, int, int]] = field(default_factory=list)
    errors_new: list[tuple[str, str]] = field(default_factory=list)
    errors_cleared: list[str] = field(default_factory=list)
    invalid_new: list[str] = field(default_factory=list)
    triggers: dict[str, str] = field(default_factory=dict)   # name -> trigger value

    @property
    def empty(self) -> bool:
        return not any(getattr(self, f) for f in self.__dataclass_fields__ if f != "triggers")

    def effects(self) -> list[tuple[str, str]]:
        return ([(n, "visible:on") for n in self.appeared] + [(n, "visible:off") for n in self.disappeared]
                + [(n, "enabled:on") for n in self.enabled] + [(n, "enabled:off") for n in self.disabled]
                + [(n, "required:on") for n in self.required_on] + [(n, "required:off") for n in self.required_off]
                + [(n, "options") for n, _, _ in self.options])


def compute_diff(ov: Overlay, prev: dict[str, list] | None, agent_names: set[str] | None = None) -> Diff:
    d = Diff()
    if not prev:
        return d
    cur = ov.snapshot()
    agent_names = agent_names or set()
    lay = ov.layout

    def collapsed(name: str, idx: int) -> bool:
        """Skip duplicates: the parent changed the same flag in the same direction."""
        n = lay.nodes[name]
        if not n.parent or n.parent not in prev:
            return False
        return prev[n.parent][idx] != cur[n.parent][idx] and cur[n.parent][idx] == cur[name][idx]

    for name in lay.order:
        if name not in cur or name not in prev:
            continue
        a, b = prev[name], cur[name]
        e = ov[name]
        if a[S_VIS] != b[S_VIS] and not collapsed(name, S_VIS):
            (d.appeared if b[S_VIS] else d.disappeared).append(name)
        if not b[S_VIS]:
            continue  # everything else only matters for visible nodes
        if a[S_DIS] != b[S_DIS] and not collapsed(name, S_DIS):
            (d.disabled if b[S_DIS] else d.enabled).append(name)
        if not e.node.is_field:
            continue
        if a[S_DISP] != b[S_DISP]:
            item = (name, a[S_DISP], b[S_DISP])
            if name in agent_names:
                d.agent_values.append(item)
            elif e.readonly or e.disabled:
                d.derived_values.append(item)
            else:
                d.user_values.append(item)
            if not (e.readonly or e.disabled):
                d.triggers[name] = b[S_TRIG]
        if a[S_REQ] != b[S_REQ] and a[S_VIS]:
            (d.required_on if b[S_REQ] else d.required_off).append(name)
        if a[S_OSIG] != b[S_OSIG]:
            d.options.append((name, a[S_OCNT], b[S_OCNT]))
        if a[S_ERR] != b[S_ERR]:
            if b[S_ERR]:
                d.errors_new.append((name, b[S_ERR]))
            else:
                d.errors_cleared.append(name)
        if b[S_INV] and not a[S_INV]:
            d.invalid_new.append(name)
    return d


# ===================================================================== dependency map


class DepStore:
    """Dependencies learned from observation: trigger (+ value) -> effect on target.

    If exactly one field changed between two messages, attribution is exact.
    If several changed, the weight is split; across many sessions false links
    fade out. Stored per jsx_hash and survives restarts (JSON file).
    Entry format: {"target|effect": {"trigger|value_id|value_name": [weight, count, exact_count]}}.
    `path=None` keeps the map in memory only.
    """

    def __init__(self, path: Path | None = None):
        self.path = path
        self.map: dict[str, dict[str, list[float]]] = defaultdict(dict)
        if self.path and self.path.exists():
            self.map.update(json.loads(self.path.read_text()))

    def observe(self, diff: Diff, ov: Overlay) -> None:
        if not diff.triggers:
            return
        effects = diff.effects()
        if not effects:
            return
        # If the batch contains dropdowns / checkboxes, treat them as the cause:
        # free-text fields rarely restructure a form.
        cats = {t: v for t, v in diff.triggers.items() if ov[t].node.role in ("select", "bool")}
        triggers = cats or diff.triggers
        w = 1 / len(triggers)
        exact = len(diff.triggers) == 1  # exactly one field changed: the cause is certain
        for target, eff in effects:
            if target in triggers:
                continue
            bucket = self.map[f"{target}|{eff}"]
            for trig, val in triggers.items():
                k = f"{trig}|{val}"
                wc = bucket.setdefault(k, [0.0, 0, 0])
                if len(wc) < 3:
                    wc.append(0)
                wc[0] += w
                wc[1] += 1
                wc[2] += exact
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.map, ensure_ascii=False, indent=1))

    @staticmethod
    def _reliable(v: list[float]) -> bool:
        """At least one exact observation, or accumulated weight from many sessions."""
        return (len(v) > 2 and v[2] >= 1) or v[0] >= 2

    def best(self, target: str, effect: str) -> tuple[str, str, int] | None:
        """(trigger, value to show, times observed)."""
        bucket = self.map.get(f"{target}|{effect}")
        if not bucket:
            return None
        k, v = max(bucket.items(), key=lambda kv: kv[1][0])
        if not self._reliable(v):
            return None
        trig, _vid, vname = k.split("|", 2)
        return trig, vname, int(v[1])

    def drivers(self) -> set[str]:
        tot: dict[str, float] = defaultdict(float)
        for bucket in self.map.values():
            for k, v in bucket.items():
                if self._reliable(v):
                    tot[k.split("|", 1)[0]] += v[0]
        return {t for t, w in tot.items() if w >= 0.99}

    def hint(self, ov: Overlay, target: str, effect: str) -> str:
        b = self.best(target, effect)
        if not b:
            return ""
        trig, vname, c = b
        lbl = ov.get(trig).label if ov.get(trig) else None
        verb = {"visible:on": "appears", "enabled:on": "becomes available"}.get(effect, "changes")
        shown = f'{trig} ("{lbl}")' if lbl else trig
        return f"usually {verb} when {shown} = {vname} (seen {c}x)"

    def effects_of(self, trigger: str) -> list[str]:
        out = []
        for key, bucket in self.map.items():
            for k, v in bucket.items():
                if k.split("|", 1)[0] == trigger and self._reliable(v):
                    target, eff = key.split("|", 1)
                    out.append(f"{target} {eff} when = {k.split('|', 2)[2]} ({int(v[1])}x)")
        return out[:8]

