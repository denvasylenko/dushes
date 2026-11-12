"""The form review (review_form): progress by section and what blocks sending.

The server computes everything it can from the form state:
- sections: required editable fields per top-level section (tabs, else the root's containers);
- errors: a field's validation error, a value no longer in the options, a required field left empty.
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
    tabs = [n for n in lay.nodes.values() if n.role == "tab"]
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


def issues(ctx: ToolCtx, warnings: Any = None, fixes: Any = None) -> list[dict]:
    from .tools import ToolError, _norm_value, form_value, reveal_chain

    ov = ctx.ov
    found: list[dict] = []
    for n in ov.layout.fields():
        e = ov[n.name]
        if not e.visible or n.role == "file":
            continue
        msg = e.error or ("the value is no longer one of the options" if e.invalid_value else
                          "required, still empty" if e.needs_input else "")
        if msg:
            found.append({"severity": "error", "field": n.name, "label": e.label or n.name, "message": str(msg)[:200]})
    for w in warnings if isinstance(warnings, list) else []:
        if not isinstance(w, dict) or w.get("field") not in ov.layout.nodes or not str(w.get("message") or "").strip():
            continue
        e = ov[w["field"]]
        item = {"severity": "warning", "field": w["field"], "label": e.label or w["field"],
                "message": str(w["message"]).strip()[:200]}
        src = w.get("source")
        if isinstance(src, (str, dict)) and src:
            item["source"] = {"title": src} if isinstance(src, str) else {k: str(v) for k, v in src.items()
                                                                          if k in ("title", "section")}
        found.append(item)
    for name, value in (fixes or {}).items() if isinstance(fixes, dict) else []:
        item = next((i for i in found if i["field"] == name and "fix" not in i), None)
        if item is None or name not in ov.layout.nodes or not ov[name].editable:
            continue
        try:
            val = _norm_value(ctx, name, value)
            item["fix"] = {"value": form_value(ctx, name, val), "display": vals.display(val)}
        except ToolError:
            continue   # the field does not accept it: the issue stays without a fix
    errs = sorted((i for i in found if i["severity"] == "error"), key=lambda i: "fix" not in i)   # fixable first
    warns = [i for i in found if i["severity"] == "warning"][:5]   # the model's warnings are never crowded out
    out = errs[:MAX_ISSUES - len(warns)] + warns
    for i in out:
        i["reveal"] = reveal_chain(ctx, i["field"])
    return out


def build(ctx: ToolCtx, mode: str, warnings: Any = None, fixes: Any = None) -> dict:
    return {"kind": "review", "mode": mode, "sections": sections(ctx), "issues": issues(ctx, warnings, fixes)}


def summary(payload: dict) -> str:
    """What the model gets back when the review is shown (before the user answers)."""
    left = sum(s["left"] for s in payload["sections"])
    errs = sum(1 for i in payload["issues"] if i["severity"] == "error")
    return f"{left} required fields left, {errs} errors, {len(payload['issues']) - errs} warnings"
