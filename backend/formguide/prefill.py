"""Prefill: fill a form from data the host application already has.

    result = await guide.suggest_prefill(state, data={"first_name": "Anna", "employer": "Acme"},
                                         text="Moved to Lyon in 2021", attachment_ids=["att_1a2b3c4d"],
                                         thread_id="t1")

Keys of `data` that are field names are normalized directly (no model call). Other keys,
free `text` and attachments go through the extraction model with the field catalog.
Every value is validated like a proposal from the agent; the result says which fields can
be filled now and which belong to steps that are still locked or hidden:

    {"values": [{"name", "label", "value", "display", "status": "now" | "later", "source", ...}],
     "errors": ["field: why it was rejected", ...], "notes": [...]}

In a chat, pass the same data as `prefill` to `FormGuide.run` (or `forwardedProps.prefill`):
the agent proposes the values it can apply now in one card and keeps the rest for later.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .attachments import extract as att
from .form.overlay import Overlay
from .form.values import display as values_display

if TYPE_CHECKING:
    from .guide import FormGuide


async def suggest_prefill(guide: FormGuide, state: dict[str, Any], *, data: dict[str, Any] | None = None,
                          text: str | None = None, attachment_ids: list[str] | None = None,
                          thread_id: str | None = None) -> dict[str, Any]:
    from .agent.tools import ToolCtx, ToolError, _norm_value, form_value

    lay = guide.layout(state.get("jsx_hash", ""))
    if lay is None:
        raise KeyError("unknown jsx_hash: call register_form first")
    pack = guide.packs.get(state.get("form_id"))
    ov = Overlay(lay, state["config"], pack.pii)
    ctx = ToolCtx(ov=ov, deps=guide.deps(lay.jsx_hash), pack=pack, loc=None)  # type: ignore[arg-type]
    values: dict[str, dict] = {}
    errors: list[str] = []
    notes: list[str] = []

    def add(name: str, raw: Any, source: str, **extra: Any) -> None:
        node = lay.nodes.get(name)
        if not node or not node.is_field:
            errors.append(f"{name}: no such field")
            return
        e = ov[name]
        if e.readonly:
            errors.append(f"{name}: read-only, computed by the form")
            return
        if node.role == "file":
            errors.append(f"{name}: files cannot be prefilled")
            return
        try:
            v = _norm_value(ctx, name, raw)
            stored = form_value(ctx, name, v)
        except ToolError as err:
            errors.append(str(err))
            return
        if e.filled and e.value == v:
            return   # already there
        values[name] = {"name": name, "label": e.label or name, "value": stored, "display": values_display(v),
                        "status": "now" if e.editable else "later",
                        "why_later": "" if e.editable else ("hidden" if not e.visible else "disabled"),
                        "source": source, **extra}

    rest: dict[str, Any] = {}
    for k, v in (data or {}).items():
        if k in lay.nodes and lay.nodes[k].is_field:
            add(k, v, "data")
        else:
            rest[k] = v

    blocks: list[dict] = []
    if rest or text:
        body = (json.dumps(rest, ensure_ascii=False, indent=1) if rest else "") + ("\n" + text if text else "")
        blocks.append({"type": "text", "text": f"<known_data>\n{body.strip()}\n</known_data>"})
    files = []
    for aid in attachment_ids or []:
        found = guide.attachments.load(thread_id or "", aid) if thread_id else None
        if not found:
            errors.append(f"{aid}: no such attachment in this conversation")
            continue
        files.append(found[0])
        blocks.append(att.file_block(found[0], att.MEDIA[att.Path(found[0]).suffix.lower()], found[1]))
    if blocks:
        names = [n for n in att.candidate_fields(ov, None, None) if n not in values]
        x = await att.extract_from_blocks(guide.models.extract, ov, blocks, names)
        for f in x.fields:
            if f.confidence != "low":
                add(f.field, f.value, ", ".join(files) or "text", confidence=f.confidence, evidence=f.evidence)
            else:
                notes.append(f"{f.field}: low confidence ({f.evidence}), not used")
        if x.notes:
            notes.append(x.notes)
    return {"values": list(values.values()), "errors": errors, "notes": notes}


def prefill_instruction(result: dict[str, Any], language: str | None) -> str:
    """The turn's 'user' text when a conversation starts from prefill data."""
    now = [v for v in result["values"] if v["status"] == "now"]
    later = [v for v in result["values"] if v["status"] == "later"]

    def line(v: dict) -> str:
        return f"- {v['name']} \"{v['label']}\" = {json.dumps(v['value'], ensure_ascii=False)} (from {v['source']})"

    parts = ["[The app opened this form with data it already has about the user. No message from the user yet.]"]
    if now:
        parts += ["Fillable now — propose these in ONE propose_changes call:", *map(line, now)]
    if later:
        parts += ["For steps that are locked or hidden now — do not propose yet; propose each when its step "
                  "becomes editable:", *map(line, later)]
    if not now and not later:
        parts.append("Nothing usable was found in the data.")
    if result["errors"]:
        parts += ["Rejected (do not use):", *(f"- {e}" for e in result["errors"])]
    parts.append("Then greet the user in one or two sentences: say what was prefilled and what the next step is.")
    parts.append(f"Reply in {language}." if language else "Reply in English unless the form is clearly in "
                                                          "another language.")
    return "\n".join(parts)
