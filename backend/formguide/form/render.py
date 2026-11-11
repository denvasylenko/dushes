"""Renders what the agent sees: outline (L0), focus (L1), changes, field cards.

Structure and order are built deterministically from the layout; labels, flags
and values come from the config. No LLM is involved in building this.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.packs import DomainPack
from .layout import Node
from .overlay import DepStore, Diff, Eff, Overlay

LEGEND = ("▶ on the user's screen · * required · ⚑ restructures the form · ⊘ disabled · "
          "🔒 read-only · ! error · ⚠ value not in options · ∅ empty")


# ===================================================================== location


@dataclass
class Location:
    on_screen: set[str]      # containers currently expanded on screen
    focus: str               # container in focus
    focused_field: str | None


def locate(ov: Overlay, ui: dict[str, Any] | None) -> Location:
    ui = ui or {}
    lay = ov.layout
    active = ui.get("activeTabs") or {}
    opened = list(ui.get("openAccordions") or [])
    on: set[str] = set()

    def visit(name: str) -> None:
        n, e = lay.nodes[name], ov[name]
        if not e.visible or not n.is_container:
            return
        on.add(name)
        if n.role == "tabs":
            tabs = [c for c in n.children if ov[c].visible]
            pick = active.get(name) if active.get(name) in tabs else (tabs[0] if tabs else None)
            if pick:
                visit(pick)
            return
        for ch in n.children:
            c = lay.nodes[ch]
            if c.role == "accordion" and ch not in opened:
                continue
            visit(ch)

    if lay.root:
        visit(lay.root)

    focused = ui.get("focused")
    focus = None
    if focused and focused in lay.nodes and ov[focused].visible:
        c = lay.nearest_container(focused)
        if c and c.name in on:
            focus = c.name
    if not focus:
        for acc in reversed(opened):
            if acc in on:
                focus = acc
                break
    if not focus:
        # the deepest expanded container
        focus = max(on, key=lambda n: lay.nodes[n].depth, default=lay.root or "")
    return Location(on, focus, focused if focused in lay.nodes else None)


# ===================================================================== lines


def _q(s: str | None) -> str:
    return f' "{s}"' if s else ""


def _req(ov: Overlay, name: str) -> str:
    done, total = ov.progress(name)
    if not total:
        return ""
    return "  ✓ done" if done == total else f"  req {done}/{total}"


def disabled_reason(ov: Overlay, deps: DepStore | None, name: str) -> str:
    """Why something is disabled: an observed dependency, otherwise a step-based guess."""
    dr = ov.disabled_root(name)
    if not dr:
        return ""
    where = f"section {dr.name} is disabled" if dr.name != name else ""
    why = deps.hint(ov, dr.name, "enabled:on") if deps else ""
    if not why:
        b = ov.blockers(dr.name)
        why = ("cause unknown; GUESS: it may be waiting for previous steps. Required empty fields "
               "earlier in the form (nearest step first): " + "; ".join(b)) if b else "cause unknown"
    return "; ".join(x for x in (where, why) if x)


def container_line(ov: Overlay, n: Node, loc: Location | None, deps: DepStore | None) -> str:
    e = ov[n.name]
    if not e.visible:
        hr = ov.hidden_root(n.name)
        why = deps.hint(ov, hr.name, "visible:on") if deps and hr else ""
        return f"{n.addr} [{n.tag} {n.name}]{_q(e.label)} — hidden{f' ({why})' if why else ''}"
    flags = ""
    if e.own_disabled:
        flags += f" ⊘ disabled, {ov.required_inside(n.name)} required inside ({disabled_reason(ov, deps, n.name)})"
    if loc and n.name in loc.on_screen:
        flags += " ▶"
        if n.role == "accordion":
            flags += " open"
    if loc and n.name == loc.focus:
        flags += " [FOCUS]"
    return f"{n.addr} [{n.tag} {n.name}]{_q(e.label)}{_req(ov, n.name)}{flags}"


def field_card(ov: Overlay, e: Eff, deps: DepStore | None, pack: DomainPack | None = None,
               full: bool = False) -> str:
    n = e.node
    parts = [f"{n.addr} {n.name} {n.tag}{'*' if e.required else ''}"]
    if e.label:
        parts.append(f'"{e.label}"')
    parts.append(f"= {ov.display_value(e)}")
    flags = []
    if deps and n.name in deps.drivers():
        flags.append("⚑")
    if not e.visible:
        hr = ov.hidden_root(n.name)
        why = deps.hint(ov, hr.name, "visible:on") if deps and hr else ""
        flags.append("hidden" + (f" by {hr.name}" if hr and hr.name != n.name else "") + (f": {why}" if why else ""))
    elif e.disabled:
        why = disabled_reason(ov, deps, n.name)
        flags.append("⊘ disabled" + (f": {why}" if why else ""))
    if e.readonly:
        flags.append("🔒")
    if e.error:
        flags.append(f'! "{e.error}"')
    if e.invalid_value:
        flags.append("⚠ value is not in the current options")
    if n.role == "select":
        o = e.options or []
        if not o:
            flags.append("options: none")
        elif len(o) <= 6 or full:
            flags.append("options: " + " | ".join(f"{x['id']}:{x['name']}" for x in o[: 30 if full else 6]))
        else:
            flags.append(f"options: {len(o)} (get_options)")
    if pack and n.name in pack.glossary and not full:
        flags.append(f"ℹ {pack.glossary[n.name][:110]}")
    ph = e.props.get("placeholder")
    if ph and not e.filled:
        flags.append(f'placeholder: "{ph}"')
    line = " ".join(parts) + (("  " + "  ".join(flags)) if flags else "")
    if full:
        path = " › ".join(ov[a.name].label for a in ov.layout.ancestors(n.name) if ov[a.name].label)
        line += f"\n  path: {path}"
        if pack and n.name in pack.glossary:
            line += f"\n  note: {pack.glossary[n.name]}"
        if deps:
            eff = deps.effects_of(n.name)
            if eff:
                line += "\n  affects: " + "; ".join(eff)
    return line


# ===================================================================== blocks


def render_outline(ov: Overlay, loc: Location, deps: DepStore, pack: DomainPack, version: int) -> str:
    lay = ov.layout
    fields = [ov[n.name] for n in lay.fields()]
    vis = [e for e in fields if e.visible]
    req = [e for e in vis if e.editable and e.required]
    errs = [e for e in vis if e.error]
    out = [
        f'FORM "{pack.title}" · config v{version} · fields visible {len(vis)}/{len(fields)} · '
        f"required filled {sum(e.filled for e in req)}/{len(req)} · errors {len(errs)}",
        LEGEND,
    ]

    def walk(name: str, depth: int) -> None:
        n = lay.nodes[name]
        if not n.is_container:
            return
        out.append("  " * depth + container_line(ov, n, loc, deps))
        if not ov[name].visible:
            return
        sub = [c for c in n.children if lay.nodes[c].is_container]
        expand = n.depth < 2 or name in loc.on_screen
        if expand:
            for c in sub:
                walk(c, depth + 1)
        elif sub:
            out.append("  " * (depth + 1) + f"(+{len(sub)} nested sections, get_outline)")

    if lay.root:
        walk(lay.root, 0)
    return "\n".join(out)


def render_container(ov: Overlay, name: str, deps: DepStore, loc: Location | None = None,
                     limit: int = 45, offset: int = 0, pack: DomainPack | None = None) -> str:
    """Direct children of a container: fields as cards, nested containers as one line."""
    lay = ov.layout
    n = lay.nodes[name]
    lines: list[str] = []
    hidden: list[str] = []
    for ch in n.children:
        c = lay.nodes[ch]
        if c.role == "static_text":
            lines.append(f'{c.addr} text: "{c.text[:160]}"')
        elif c.is_container:
            lines.append(container_line(ov, c, loc, deps))
            if c.role == "tabs" and ov[ch].visible:
                for t in c.children:
                    lines.append("  " + container_line(ov, lay.nodes[t], loc, deps))
        elif ov[ch].visible:
            lines.append(field_card(ov, ov[ch], deps, pack))
        else:
            hidden.append(field_card(ov, ov[ch], deps) if deps.best(ch, "visible:on") else ch)
    page = lines[offset: offset + limit]
    rest = len(lines) - offset - len(page)
    if rest > 0:
        page.append(f"… {rest} more (get_fields offset={offset + limit})")
    if hidden:
        page.append("hidden fields here: " + "; ".join(hidden))
    return "\n".join(page)


def render_focus(ov: Overlay, loc: Location, deps: DepStore, pack: DomainPack | None = None) -> str:
    n = ov.layout.nodes.get(loc.focus)
    if not n:
        return ""
    e = ov[n.name]
    head = f"FOCUS {n.addr} [{n.tag} {n.name}]{_q(e.label)}"
    if loc.focused_field:
        fe = ov.get(loc.focused_field)
        head += f" · cursor in field {loc.focused_field}" + (_q(fe.label) if fe else "")
    return head + "\n" + render_container(ov, n.name, deps, loc, pack=pack)


def render_changes(ov: Overlay, d: Diff, v_from: int, v_to: int, limit: int = 30) -> str:
    if d.empty:
        return f"CHANGES v{v_from} → v{v_to}: none"

    def lbl(name: str) -> str:
        e = ov.get(name)
        return f"{name}{_q(e.label) if e else ''}"

    def req_in(name: str) -> str:
        n = ov.layout.nodes[name]
        if not n.is_container:
            return ""
        _, total = ov.progress(name)
        return f" ({total} required)" if total else ""

    lines = []
    if d.user_values:
        lines.append("user: " + "; ".join(f"{n} {a} → {b}" for n, a, b in d.user_values))
    if d.agent_values:
        lines.append("agent (confirmed by user): " + "; ".join(f"{n} {a} → {b}" for n, a, b in d.agent_values))
    form = []
    form += [f"+ appeared {lbl(n)}{req_in(n)}" for n in d.appeared]
    form += [f"− hidden {lbl(n)}" for n in d.disappeared]
    form += [f"⊘→✓ became available {lbl(n)}" for n in d.enabled]
    form += [f"✓→⊘ became disabled {lbl(n)}" for n in d.disabled]
    form += [f"* became required {lbl(n)}" for n in d.required_on]
    form += [f"no longer required {lbl(n)}" for n in d.required_off]
    form += [f"options {n}: {a} → {b}" for n, a, b in d.options]
    form += [f"⚠ {lbl(n)}: the selected value is no longer in the options" for n in d.invalid_new]
    form += [f'! error {n}: "{m}"' for n, m in d.errors_new]
    form += [f"error fixed: {n}" for n in d.errors_cleared]
    form += [f"🔒 {n}: {a} → {b}" for n, a, b in d.derived_values]
    if len(form) > limit:
        form = form[:limit] + [f"… {len(form) - limit} more"]
    if form:
        lines.append("form reacted:\n  " + "\n  ".join(form))
    return f"CHANGES v{v_from} → v{v_to}:\n" + "\n".join(lines)
