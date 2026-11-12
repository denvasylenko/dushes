"""The form review (review_form): progress by section and what blocks sending.

The server computes everything it can from the form state:
- sections: required editable fields per top-level section (the outermost tabs, else the root's containers);
- errors: a field's validation error or a value no longer in the options. They always come first and are
  never crowded out;
- missing: required fields still empty, only in `submit` mode (in `status` the sections show them), one row
  per section ("Passport: 5 fields still empty", kind "missing", Show opens the first one).
The model may add warnings (a rule or document flags a valid value) and fix values; fixes are validated
like proposed changes and dropped when the field does not accept them.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..form import values as vals

if TYPE_CHECKING:
    from .tools import ToolCtx

MAX_ISSUES = 20


def sections(ctx: ToolCtx) -> list[dict]:
    from .tools import reveal_chain

    lay, ov = ctx.ov.layout, ctx.ov
    # the outermost tabs only: a tab inside another tab is part of its section, not a section of its own
    tabs = [n for n in lay.nodes.values() if n.role == "tab" and not any(a.role == "tab" for a in lay.ancestors(n.name))]
    if not tabs and lay.root:
        tabs = [lay.nodes[c] for c in lay.nodes[lay.root].children if lay.nodes[c].is_container]
    out = []
    for n in tabs:
        e = ov[n.name]
        if not e.visible:
            continue
        done, total = ov.progress(n.name)
        if total:
            out.append({"name": n.name, "label": e.label or n.name, "left": total - done, "total": total,
                        "reveal": reveal_chain(ctx, n.name)})
    return out


def _section_of(ctx: ToolCtx, name: str, tops: dict[str, str]) -> str:
    for a in ctx.ov.layout.ancestors(name):
        if a.name in tops:
            return a.name
    return ""


def _fixes(ctx: ToolCtx, fixes: Any) -> dict[str, dict]:
    """The model's fix values that the fields accept: {field: {value (form format), display}}."""
    from .tools import ToolError, _norm_value, form_value

    out: dict[str, dict] = {}
    for name, value in (fixes or {}).items() if isinstance(fixes, dict) else []:
        if name not in ctx.ov.layout.nodes or not ctx.ov[name].editable:
            continue
        try:
            val = _norm_value(ctx, name, value)
            out[name] = {"value": form_value(ctx, name, val), "display": vals.display(val)}
        except ToolError:
            continue   # the field does not accept it: the issue stays without a fix
    return out


def issues(ctx: ToolCtx, warnings: Any = None, fixes: Any = None, mode: str = "status") -> list[dict]:
    """Errors first (fixable first, never crowded out), then the missing fields per section, then warnings."""
    from .tools import reveal_chain

    ov = ctx.ov
    fix = _fixes(ctx, fixes)
    errs: list[dict] = []
    missing: dict[str, list[str]] = {}   # section -> required empty fields, in form order
    tops = {s["name"]: s["label"] for s in sections(ctx)}
    for n in ov.layout.fields():
        e = ov[n.name]
        if not e.visible or n.role == "file":
            continue
        msg = e.error or ("the value is no longer one of the options" if e.invalid_value else "")
        if msg:
            errs.append({"severity": "error", "field": n.name, "label": e.label or n.name, "message": str(msg)[:200]})
        elif e.needs_input and n.name in fix:   # an empty field the model can fill: its own row, with Fix
            errs.append({"severity": "error", "kind": "missing", "field": n.name, "label": e.label or n.name,
                         "message": "required, still empty"})
        elif e.needs_input and mode == "submit":
            missing.setdefault(_section_of(ctx, n.name, tops), []).append(n.name)
    for i in errs:
        if i["field"] in fix:
            i["fix"] = fix[i["field"]]
    errs.sort(key=lambda i: ("fix" not in i, i.get("kind") == "missing"))   # fixable first, then real errors
    gaps = [{"severity": "error", "kind": "missing", "field": names[0],
             "label": tops.get(sec) or ov[names[0]].label or names[0],
             "message": f"{len(names)} required field{'s' if len(names) > 1 else ''} still empty"}
            for sec, names in missing.items()]
    warns: list[dict] = []
    for w in warnings if isinstance(warnings, list) else []:
        if not isinstance(w, dict) or w.get("field") not in ov.layout.nodes or not str(w.get("message") or "").strip():
            continue
        item = {"severity": "warning", "field": w["field"], "label": ov[w["field"]].label or w["field"],
                "message": str(w["message"]).strip()[:200]}
        src = w.get("source")
        if isinstance(src, (str, dict)) and src:
            item["source"] = {"title": src} if isinstance(src, str) else {k: str(v) for k, v in src.items()
                                                                          if k in ("title", "section")}
        warns.append(item)
    out = (errs + gaps)[:MAX_ISSUES] + warns[:5]   # the model's warnings are never crowded out
    for i in out:
        i["reveal"] = reveal_chain(ctx, i["field"])
    return out


def build(ctx: ToolCtx, mode: str, warnings: Any = None, fixes: Any = None) -> dict:
    return {"kind": "review", "mode": mode, "sections": sections(ctx), "issues": issues(ctx, warnings, fixes, mode)}


def summary(payload: dict) -> str:
    """What the model gets back when the review is shown (before the user answers)."""
    left = sum(s["left"] for s in payload["sections"])
    errs = sum(1 for i in payload["issues"] if i["severity"] == "error")
    return f"{left} required fields left, {errs} errors, {len(payload['issues']) - errs} warnings"
