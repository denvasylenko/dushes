"""Agent tools. All are read-only except two with a UI side effect:

- focus_field     -> a UI directive for the frontend (open tabs/accordions, highlight);
- propose_changes -> validated, then goes to an interrupt (the user confirms);
- ask_user        -> a question card with clickable options or a typed answer (date, number...), an interrupt;
- request_file    -> asks the user to upload a document, an interrupt (answered with attachment ids);
- confirm_action  -> a yes/no confirmation before an action with side effects, an interrupt.

Two tools delegate to separate model calls, so their inputs never enter the main context:
- ask_documents           -> the deep-agent researcher over the form's business documents;
- extract_from_attachment -> reads a file the user attached and returns field values.

`use_skill` loads a skill's instructions. Tools contributed by skills or by the
config (any LangChain BaseTool) run here too, after the built-in ones.

The agent cannot "write" the config: the config belongs to the form backend.
The frontend applies changes through the same path as user input.
"""
from __future__ import annotations

import json
import re

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from ..attachments import extract as att
from . import review
from .actions import off as switchable_off
from ..domain.packs import DomainPack

if TYPE_CHECKING:
    from ..guide import FormGuide
from ..form import values as vals
from ..form.layout import CHOICE
from .interaction import input_ok as interaction_ok
from ..form.overlay import DepStore, Overlay
from ..form.render import Location, container_line, disabled_reason, field_card, render_container
from ..form.search import search

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_outline",
        "description": "Structure of a form section (containers only, with progress). Use it to expand a "
                       "collapsed branch of the outline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "container name; empty = the whole form"},
                "depth": {"type": "integer", "description": "depth, default 3"},
            },
        },
    },
    {
        "name": "get_fields",
        "description": "Fields and subsections inside a container (tab, accordion) with current values and flags.",
        "input_schema": {
            "type": "object",
            "properties": {"container": {"type": "string"}, "offset": {"type": "integer"}},
            "required": ["container"],
        },
    },
    {
        "name": "get_field",
        "description": "Full information about a field: path, value, flags, options, the note from the form's "
                       "knowledge base and known dependencies.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "search_fields",
        "description": "Find fields by meaning (e.g. 'tax id', 'home address', 'income'), in any language. "
                       "Also searches hidden fields.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "get_options",
        "description": "Options of a dropdown (optionally filtered by text).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "query": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "ask_user",
        "description": "Ask the user one question with clickable options and wait for the answer. Use it when "
                       "the user must choose between known options or settle an ambiguity (e.g. which loan "
                       "type). Pass `field` to offer that field's current options (optionally `options` to offer "
                       "only some of them). Never use it to confirm values: propose_changes does that.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": "array", "description": "choices: strings or {id, label, description?, attrs?}; "
                                                            "omit for a typed answer or to offer all of `field`'s options",
                            "items": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {
                                "id": {"type": "string"}, "label": {"type": "string"},
                                "description": {"type": "string", "description": "one short line under the option"},
                                "attrs": {"type": "object", "description": "short facts to compare, the same keys on "
                                          "every option, e.g. {\"Rate\": \"16.9%\"}; only from the form, rules or documents"}}}]}},
                "recommended": {"type": "string", "description": "the id of the option that fits best, if one clearly does"},
                "suggested": {"type": "array", "items": {"type": "string"},
                              "description": "up to 5 likely option ids to show first in a long list"},
                "fields": {"type": "array", "description": "instead of options: 2-3 short editable fields asked together "
                           "(e.g. first and last name); the answers fill them",
                           "items": {"type": "object", "properties": {"name": {"type": "string"},
                                                                       "required": {"type": "boolean"}},
                                     "required": ["name"]}},
                "field": {"type": "string", "description": "a dropdown, radio or multi-select field"},
                "multiple": {"type": "boolean", "description": "several choices allowed"},
                "allow_text": {"type": "boolean", "description": "a typed answer allowed; default true"},
                "input": {"type": "object", "description": "the kind of typed answer, shown as a picker",
                          "properties": {"type": {"type": "string",
                                                  "enum": ["text", "number", "date", "time", "datetime", "address"]},
                                         "min": {"type": ["string", "number"]}, "max": {"type": ["string", "number"]}}},
            },
            "required": ["question"],
        },
    },
    {
        "name": "request_file",
        "description": "Ask the user to upload a document (passport scan, payslip...) and wait for it. Then read it "
                       "with extract_from_attachment. Use it when a document would save typing or is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "what to upload, one short sentence"},
                "accept": {"type": "string", "description": "file types, e.g. '.pdf,.jpg'; default: all supported"},
                "multiple": {"type": "boolean"},
                "field": {"type": "string", "description": "the file field this document is for, if any"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "confirm_action",
        "description": "Ask the user to confirm an action with side effects (submitting, sending, cancelling) "
                       "before you call the tool that does it. Not for field values: propose_changes confirms those.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"}, "message": {"type": "string"},
                "confirm_label": {"type": "string", "description": "the confirm button, e.g. 'Submit'"},
                "danger": {"type": "boolean", "description": "the action cannot be undone"},
                "details": {"type": "array", "description": "what is sent, up to 6 short rows",
                            "items": {"type": "object", "properties": {"label": {"type": "string"},
                                                                       "value": {"type": "string"}},
                                      "required": ["label", "value"]}},
                "consequence": {"type": "string", "description": "one sentence, e.g. 'You can't edit it after sending.'"},
            },
            "required": ["title", "message"],
        },
    },
    {
        "name": "review_form",
        "description": "Show the user a review of the form and wait: what is left per section and what blocks "
                       "sending (computed from the form). mode status: progress when the user asks what is left; "
                       "mode submit: the check before sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["status", "submit"]},
                "warnings": {"type": "array", "description": "valid values a rule or document flags",
                             "items": {"type": "object", "properties": {
                                 "field": {"type": "string"}, "message": {"type": "string"},
                                 "source": {"type": "string", "description": "document title > section"}},
                                 "required": ["field", "message"]}},
                "fixes": {"type": "object", "description": "{field: corrected value} for errors you can fix with "
                                                           "data the user gave (e.g. the phone in the right format)"},
            },
            "required": ["mode"],
        },
    },
    {
        "name": "focus_field",
        "description": "Show a field or section to the user: the frontend opens the needed tabs and accordions, "
                       "scrolls and highlights the element with a hint. Works only for visible elements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "hint": {"type": "string", "description": "a short hint shown next to the field, in the user's language"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "propose_changes",
        "description": "Propose filling fields with values the user gave in the chat. The user sees a card and "
                       "confirms or rejects it. For dropdowns and radio groups pass the option id; for "
                       "multi-selects a list of option ids. Dates: YYYY-MM-DD. "
                       "A dropdown whose options depend on another field in the same call (a car model after "
                       "its make) may be included with the option's name: it is applied after the others. "
                       "Only the user can upload files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": ["string", "number", "boolean", "array"], "items": {"type": "string"}},
                            "reason": {"type": "string"},
                            "issue": {"type": "string", "description": "only when a rule or document flags this "
                                      "valid value (e.g. income low for the payment): one short sentence"},
                        },
                        "required": ["name", "value"],
                    },
                }
            },
            "required": ["changes"],
        },
    },
]
TOOLS += [
    {
        "name": "ask_documents",
        "description": "Ask the business's documents for this form (conditions, requirements, prices, policies, "
                       "limits). A researcher reads them and returns a short answer with sources. Slower than "
                       "other tools: use it only when the business rules in your instructions do not settle it.",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "a self-contained question, with any "
                                                                          "relevant facts the user gave"}},
            "required": ["question"],
        },
    },
    {
        "name": "use_skill",
        "description": "Load the full instructions of one of the skills listed in your instructions before "
                       "doing that kind of task.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
    {
        "name": "extract_from_attachment",
        "description": "Read a file the user attached (scan, photo, PDF, text) and get values for form fields. "
                       "Returns values with confidence and evidence; it does not fill anything.",
        "input_schema": {
            "type": "object",
            "properties": {
                "attachment_id": {"type": "string"},
                "fields": {"type": "array", "items": {"type": "string"},
                           "description": "candidate field names; omit to consider the whole form"},
                "container": {"type": "string", "description": "or: only fields inside this section"},
            },
            "required": ["attachment_id"],
        },
    },
]
BUILTIN = {t["name"] for t in TOOLS}


def tool_schemas(extra: list[BaseTool], actions: frozenset[str] | None = None) -> list[Any]:
    """Built-in tools in the provider-neutral (OpenAI function) format + extra LangChain tools.
    `actions`: the switchable actions on in this run (None = all); the others are left out."""
    hidden = switchable_off(actions) if actions is not None else frozenset()
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}}
            for t in TOOLS if t["name"] not in hidden] + list(extra)


@dataclass
class ToolCtx:
    ov: Overlay
    deps: DepStore
    pack: DomainPack
    loc: Location
    ui_directives: list[dict] = field(default_factory=list)
    pending_changes: list[dict] | None = None
    pending_interaction: dict | None = None      # a card that waits for the user: {kind: ask|upload|confirm, ...}
    confirm_tools: frozenset[str] = frozenset()  # tools that always need the user's confirmation first
    thread_id: str = ""
    emit: Callable[[dict], None] | None = None   # progress events for the UI
    guide: FormGuide | None = None               # access to models, knowledge, attachments, skills
    extra_tools: dict[str, BaseTool] = field(default_factory=dict)
    actions: frozenset[str] | None = None        # switchable actions on in this run; None = all (agent/actions.py)
    last_extraction: dict | None = None          # the thread's last read document: {title, attachment_id, values}
    turn_sources: list[dict] | None = None       # documents the researcher cited this turn: [{title, section?}]
    pending_source: dict | None = None           # the card's source header (values from a document)
    caps: frozenset[str] | None = None           # what the client renders; None = everything

    def can(self, variant: str) -> bool:
        return self.caps is None or variant in self.caps


class ToolError(Exception):
    pass


def _check_args(name: str, args: Any) -> dict:
    schema = next((t["input_schema"] for t in TOOLS if t["name"] == name), None)
    if schema is None:
        raise ToolError(f"unknown tool {name}")
    if not isinstance(args, dict):
        raise ToolError("INVALID_JSON: an object is expected")
    for r in schema.get("required", []):
        if r not in args:
            raise ToolError(f"INVALID_JSON: missing required field {r}")
    return args


def _need(ctx: ToolCtx, name: str):
    n = ctx.ov.layout.get(name)
    if not n:
        raise ToolError(f"no element with name={name!r}. Use search_fields.")
    return n


async def run_tool(name: str, raw_args: Any, ctx: ToolCtx) -> str:
    if ctx.actions is not None and name in switchable_off(ctx.actions):
        return f"ERROR: {name} is not available in this chat (switched off, or the client cannot show it)."
    if name not in BUILTIN and name in ctx.extra_tools:
        try:
            out = await ctx.extra_tools[name].ainvoke(raw_args or {})
        except Exception as e:  # noqa: BLE001 — report tool failures to the model
            raise ToolError(f"{name} failed: {type(e).__name__}: {e}") from None
        if isinstance(out, dict) and isinstance(out.get("receipt"), dict):   # a host action's receipt for the user
            r = {k: str(v)[:80] for k, v in out["receipt"].items() if k in ("title", "number", "eta") and v}
            if ctx.emit and ctx.can("confirm.receipt"):
                ctx.emit({"kind": "receipt", "receipt": r})
            rest = {k: v for k, v in out.items() if k != "receipt"}
            return json.dumps({**rest, "receipt": r}, ensure_ascii=False)
        return out if isinstance(out, str) else str(getattr(out, "content", out))
    args = _check_args(name, raw_args)
    async_impl = globals().get(f"_ta_{name}")
    if async_impl:
        return await async_impl(args, ctx)
    return globals()[f"_t_{name}"](args, ctx)


# ---------------------------------------------------------------- read-only


def _t_get_outline(a: dict, ctx: ToolCtx) -> str:
    ov, lay = ctx.ov, ctx.ov.layout
    root = a.get("container") or lay.root
    _need(ctx, root)
    depth = int(a.get("depth") or 3)
    out: list[str] = []

    def walk(name: str, d: int) -> None:
        n = lay.nodes[name]
        if not n.is_container:
            return
        out.append("  " * d + container_line(ov, n, ctx.loc, ctx.deps))
        if d >= depth or not ov[name].visible:
            return
        for c in n.children:
            walk(c, d + 1)

    walk(root, 0)
    return "\n".join(out)


def _t_get_fields(a: dict, ctx: ToolCtx) -> str:
    n = _need(ctx, a["container"])
    if not n.is_container:
        raise ToolError(f"{n.name} is a field, not a container. Use get_field.")
    head = container_line(ctx.ov, n, ctx.loc, ctx.deps)
    body = render_container(ctx.ov, n.name, ctx.deps, ctx.loc, offset=int(a.get("offset") or 0), pack=ctx.pack)
    return head + "\n" + body


def _t_get_field(a: dict, ctx: ToolCtx) -> str:
    n = _need(ctx, a["name"])
    if n.is_container:
        return _t_get_fields({"container": n.name}, ctx)
    return field_card(ctx.ov, ctx.ov[n.name], ctx.deps, ctx.pack, full=True)


def _t_search_fields(a: dict, ctx: ToolCtx) -> str:
    hits = search(ctx.ov, ctx.pack, a["query"])
    if not hits:
        return "nothing found"
    lines = []
    for _s, name in hits:
        ov = ctx.ov
        path = " › ".join(ov[x.name].label for x in ov.layout.ancestors(name) if ov[x.name].label)
        lines.append(f"{field_card(ov, ov[name], ctx.deps, ctx.pack)}\n  path: {path}")
    return "\n".join(lines)


def _t_get_options(a: dict, ctx: ToolCtx) -> str:
    n = _need(ctx, a["name"])
    e = ctx.ov[n.name]
    if n.role not in CHOICE and n.role != "multiselect":
        raise ToolError(f"{n.name} is not a dropdown, radio group or multi-select")
    opts = e.options or []
    q = (a.get("query") or "").lower()
    if q:
        opts = [o for o in opts if q in o["name"].lower() or q in str(o["id"]).lower()]
    if not opts:
        return "no options" + (" (the list is empty: it probably depends on another field)" if not e.options else "")
    return "\n".join(f"{o['id']}: {o['name']}" for o in opts[:40]) + (
        f"\n… {len(opts) - 40} more" if len(opts) > 40 else "")


# ---------------------------------------------------------------- UI


def reveal_chain(ctx: ToolCtx, name: str) -> list[dict]:
    lay = ctx.ov.layout
    chain = []
    for n in lay.ancestors(name) + [lay.nodes[name]]:
        if n.role == "tab":
            chain.append({"type": "tab", "tabs": n.parent, "tab": n.name})
        elif n.role == "accordion":
            chain.append({"type": "accordion", "name": n.name})
    return chain


def _t_focus_field(a: dict, ctx: ToolCtx) -> str:
    n = _need(ctx, a["name"])
    e = ctx.ov[n.name]
    if not e.visible:
        hr = ctx.ov.hidden_root(n.name)
        why = ctx.deps.hint(ctx.ov, hr.name, "visible:on") if hr else ""
        raise ToolError(f"{n.name} is hidden right now (hidden by {hr.name if hr else n.name})."
                        + (f" {why}." if why else " The condition for it to appear is not known yet."))
    d = {"type": "focus", "target": n.name, "reveal": reveal_chain(ctx, n.name), "hint": a.get("hint") or ""}
    ctx.ui_directives.append(d)
    path = " › ".join(f"{s['type']} {s.get('tab') or s.get('name')}" for s in d["reveal"])
    note = f" (currently not editable: {disabled_reason(ctx.ov, ctx.deps, n.name)})" if e.disabled else ""
    return f"ok: shown {n.name} to the user{note}; opened: {path}"


# ---------------------------------------------------------------- changes

def _choice(e, name: str, value: Any) -> dict:
    o = vals.find_option(e.options, value)
    if o:
        return {"id": o["id"], "name": o["name"]}
    avail = ", ".join(f"{x['id']}:{x['name']}" for x in (e.options or [])[:12]) or "the list is empty"
    raise ToolError(f"{name}: there is no option {value!r}. Available: {avail}")


def _norm_value(ctx: ToolCtx, name: str, value: Any) -> Any:
    """The model's value -> the canonical value of the field's role (form/values.py), or ToolError."""
    e = ctx.ov[name]
    role = e.node.role
    if role in CHOICE:
        return _choice(e, name, value)
    if role == "multiselect":
        items = vals._split_list(value)
        if not items:
            raise ToolError(f"{name}: a list of options is expected")
        out, bad = [], []
        for it in items:
            try:
                c = _choice(e, name, it)
                if c not in out:
                    out.append(c)
            except ToolError:
                bad.append(repr(it))
        if bad:
            avail = ", ".join(f"{x['id']}:{x['name']}" for x in (e.options or [])[:12]) or "the list is empty"
            raise ToolError(f"{name}: there is no option {', '.join(bad)}. Available: {avail}")
        return out
    if role == "bool":
        b = vals._bool_of(None, value)
        if b is None:
            raise ToolError(f"{name}: true/false expected")
        return b
    if role == "date":
        try:
            return vals.parse_date(str(value), "iso")
        except ValueError:
            raise ToolError(f"{name}: date expected as YYYY-MM-DD") from None
    if role == "number":
        try:
            return vals.parse_number(value)
        except (ValueError, TypeError):
            raise ToolError(f"{name}: a number is expected") from None
    if role == "file":
        raise ToolError(f"{name}: only the user can upload a file. Show the field with focus_field.")
    return str(value)


def previous_of(ctx_or_ov: Any, name: str) -> dict:
    """The field's value before a change: {previous (the form's format), previous_display} or nulls."""
    ov = getattr(ctx_or_ov, "ov", ctx_or_ov)
    e = ov[name]
    if not e.filled:
        return {"previous": None, "previous_display": None}
    if e.unreadable:
        return {"previous": e.raw, "previous_display": str(e.raw)}
    return {"previous": e.raw, "previous_display": vals.display(e.value)}


def form_value(ctx_or_ov: Any, name: str, value: Any) -> Any:
    """A canonical value written in the form's own format (the field spec), or ToolError."""
    ov = getattr(ctx_or_ov, "ov", ctx_or_ov)
    e = ov[name]
    try:
        return vals.encode(e.spec, e.node.role, value, e.options, e.props)
    except vals.CodecError as err:
        raise ToolError(f"{name}: {err}") from None


def _waiting(ctx: ToolCtx) -> bool:
    return ctx.pending_changes is not None or ctx.pending_interaction is not None


WAITING = "a card or question is already waiting for the user. One at a time: call it in a later step."
MAX_QUESTION_OPTIONS = 12      # options the model writes itself
MAX_FIELD_OPTIONS = 500        # a field's own options attached by the server (a searchable list)
MAX_QUESTION_FIELDS = 3


def _t_ask_user(a: dict, ctx: ToolCtx) -> str:
    if _waiting(ctx):
        raise ToolError(WAITING)
    question = str(a.get("question") or "").strip()
    if not question:
        raise ToolError("question must not be empty")
    if len(question) > 300:
        raise ToolError("the question is too long (300 characters at most); ask one short question")
    raw = a.get("options") or []
    if not isinstance(raw, list):
        raise ToolError("options must be a list")
    multiple = a.get("multiple")
    field_name = a.get("field")
    opts: list[dict] = []
    if field_name:
        n = _need(ctx, field_name)
        e = ctx.ov[n.name]
        if n.role in ("date", "number") and not raw:   # a typed answer with a picker of the field's type
            a = {**a, "input": a.get("input") or {"type": n.role}}
        elif n.role not in CHOICE and n.role != "multiselect":
            raise ToolError(f"{n.name} is not a dropdown, radio group or multi-select; pass your own options")
        elif not e.options:
            raise ToolError(f"{n.name} has no options right now (they probably depend on another field)")
        elif raw:
            bad = []
            for x in raw:
                key = (x.get("id") or x.get("label")) if isinstance(x, dict) else x
                o = vals.find_option(e.options, key)
                if o is None:
                    bad.append(repr(key))
                elif not any(str(p["id"]) == str(o["id"]) for p in opts):
                    opts.append({"id": str(o["id"]), "label": o["name"], **_details(x)})
            if bad:
                raise ToolError(f"{n.name}: no option {', '.join(bad)}. Use get_options to see them.")
        else:
            opts = [{"id": str(o["id"]), "label": o["name"]} for o in e.options]
        if multiple is None:
            multiple = n.role == "multiselect"
        field_name = n.name
    else:
        for x in raw:
            if isinstance(x, dict):
                label = str(x.get("label") or x.get("id") or "").strip()
                oid = str(x.get("id") or label).strip()
            else:
                label = oid = str(x).strip()
            if label and not any(p["id"] == oid for p in opts):
                opts.append({"id": oid, "label": label, **_details(x)})
    from_field = bool(field_name) and not raw
    searchable = from_field and ctx.can("ask.search")   # the client shows a long list with search
    if searchable and len(opts) > MAX_FIELD_OPTIONS:
        raise ToolError(f"{field_name} has {len(opts)} options ({MAX_FIELD_OPTIONS} at most in a card); "
                        "ask in text or offer the likely ones with `options`.")
    if not searchable and len(opts) > MAX_QUESTION_OPTIONS:
        raise ToolError(f"too many options ({len(opts)}; {MAX_QUESTION_OPTIONS} at most). Offer only the likely "
                        "ones with `options`, or ask in text.")
    allow_text = a.get("allow_text")
    allow_text = True if allow_text is None else bool(allow_text)
    inp = _question_input(a.get("input"))
    if inp and field_name and inp.get("type") == "number":
        inp = _range_from_field(ctx, field_name, inp)
    if inp and inp.get("type") == "address" and not ctx.can("ask.address"):
        inp = {"type": "text"}
    if inp:
        allow_text = True
    asked = _question_fields(ctx, a.get("fields"))
    if asked:
        opts, allow_text, inp, field_name = [], False, None, None
    if not opts and not allow_text and not asked:
        raise ToolError("a question without options must allow a typed answer")
    _clean_details(opts, ctx)
    payload: dict[str, Any] = {"kind": "ask", "question": question, "options": opts,
                               "multiple": bool(multiple) and bool(opts), "allow_text": allow_text,
                               **({"input": inp} if inp else {}), **({"field": field_name} if field_name else {})}
    if asked:
        payload["fields"] = asked
    if ctx.turn_sources and any(o.get("attrs") for o in opts):
        payload["sources"] = ctx.turn_sources
    ids = {o["id"] for o in opts}
    rec = str(a.get("recommended") or "")
    if rec in ids and ctx.can("ask.details"):
        payload["recommended"] = rec
    sug = [str(i) for i in a.get("suggested") or [] if str(i) in ids][:5] if isinstance(a.get("suggested"), list) else []
    if sug and len(opts) > MAX_QUESTION_OPTIONS:
        payload["suggested"] = list(dict.fromkeys(sug))
    if field_name and opts:
        payload.update(_applying(ctx, field_name, opts))
    elif field_name and inp and inp.get("type") in ("date", "number", "time") and ctx.ov[field_name].editable:
        # a typed answer about a date / number field fills it as written (ISO date, HH:MM, a number)
        payload.update(applies=True, label=ctx.ov[field_name].label or field_name, **previous_of(ctx, field_name))
    if field_name:   # where the field is: the client shows it once the answer fills it
        payload["reveal"] = reveal_chain(ctx, field_name)
    ctx.pending_interaction = payload
    return ""


def _applying(ctx: ToolCtx, name: str, opts: list[dict]) -> dict:
    """A question about an editable choice field fills it when answered: each option carries its value in
    the form's own format, and the card carries the field's previous value (for Undo)."""
    e = ctx.ov[name]
    if not e.editable or (e.node.role not in CHOICE and e.node.role != "multiselect"):
        return {}
    try:
        for o in opts:
            found = vals.find_option(e.options, o["id"])
            if found is None:
                return {}
            choice = {"id": found["id"], "name": found["name"]}
            o["value"] = (form_value(ctx, name, [choice])[0] if e.node.role == "multiselect"
                          else form_value(ctx, name, choice))
    except ToolError:
        for o in opts:
            o.pop("value", None)
        return {}
    return {"applies": True, "label": e.label or name, **previous_of(ctx, name)}


INPUT_TYPES = ("text", "number", "date", "time", "datetime", "address")


def _details(x: Any) -> dict:
    """description / attrs the model gave an option (trimmed)."""
    if not isinstance(x, dict):
        return {}
    out: dict[str, Any] = {}
    d = str(x.get("description") or "").strip()
    if d:
        out["description"] = d[:120]
    at = x.get("attrs")
    if isinstance(at, dict) and at:
        out["attrs"] = {str(k)[:24]: str(v)[:40] for k, v in list(at.items())[:5]}
    return out


def _clean_details(opts: list[dict], ctx: ToolCtx) -> None:
    """Drop what the client cannot show; attrs only when 2+ options share the same keys."""
    keys = [tuple(sorted(o["attrs"])) for o in opts if o.get("attrs")]
    shared = len(keys) >= 2 and len(set(keys)) == 1
    for o in opts:
        if not ctx.can("ask.details"):
            o.pop("description", None)
        if not (shared and ctx.can("ask.compare")):
            o.pop("attrs", None)


def _range_from_field(ctx: ToolCtx, name: str, inp: dict) -> dict:
    """A number question about a field: min / max / step / unit from the field's props (the model may narrow)."""
    props = ctx.ov[name].props
    out = dict(inp)
    for k in ("min", "max"):
        v = props.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            mine = out.get(k)
            try:
                narrower = mine is not None and (float(mine) > v if k == "min" else float(mine) < v)
            except (TypeError, ValueError):
                narrower = False
            out[k] = mine if narrower else v
    if ctx.can("ask.range"):
        if isinstance(props.get("step"), (int, float)) and not isinstance(props.get("step"), bool) and props["step"] > 0:
            out["step"] = props["step"]
        unit = props.get("unit") or props.get("suffix")
        if isinstance(unit, str) and unit.strip():
            out["unit"] = unit.strip()[:12]
    return out


def _question_fields(ctx: ToolCtx, raw: Any) -> list[dict]:
    """`fields` of ask_user: 2-3 editable text / number / date fields asked in one card."""
    if not raw:
        return []
    if not ctx.can("ask.multi"):
        raise ToolError("this chat cannot ask several fields in one card; ask one question at a time")
    if not isinstance(raw, list) or not 2 <= len(raw) <= MAX_QUESTION_FIELDS:
        raise ToolError(f"fields must list 2 to {MAX_QUESTION_FIELDS} fields")
    out = []
    for f in raw:
        name = f.get("name") if isinstance(f, dict) else f
        n = _need(ctx, str(name))
        e = ctx.ov[n.name]
        if not n.is_field or n.role not in ("text", "number", "date"):
            raise ToolError(f"{n.name}: only text, number and date fields can be asked together")
        if not e.editable:
            raise ToolError(f"{n.name} cannot be edited right now")
        item: dict[str, Any] = {"name": n.name, "label": e.label or n.name,
                                "required": bool(f.get("required", e.required)) if isinstance(f, dict) else e.required}
        if n.role != "text":
            item["input"] = _range_from_field(ctx, n.name, {"type": n.role}) if n.role == "number" else {"type": n.role}
        out.append(item)
    if len({x["name"] for x in out}) != len(out):
        raise ToolError("fields must be different")
    return out


def _question_input(raw: Any) -> dict | None:
    """`input` of ask_user: {type, min?, max?}; bounds are checked to match the type."""
    if not raw:
        return None
    if not isinstance(raw, dict) or raw.get("type") not in INPUT_TYPES:
        raise ToolError(f"input.type must be one of {', '.join(INPUT_TYPES)}")
    out: dict[str, Any] = {"type": raw["type"]}
    for k in ("min", "max"):
        if raw.get(k) in (None, ""):
            continue
        if not interaction_ok(out["type"], raw[k]):
            raise ToolError(f"input.{k} {raw[k]!r} is not a valid {out['type']}")
        out[k] = raw[k]
    return out


def _t_request_file(a: dict, ctx: ToolCtx) -> str:
    if _waiting(ctx):
        raise ToolError(WAITING)
    prompt = str(a.get("prompt") or "").strip()
    if not prompt:
        raise ToolError("prompt must not be empty")
    supported = list(att.MEDIA)
    wanted = [x.strip().lower() for x in str(a.get("accept") or "").replace(";", ",").split(",") if x.strip()]
    wanted = [x if x.startswith(".") else "." + x.split("/")[-1] for x in wanted]
    accept = [x for x in wanted if x in supported] or supported
    payload: dict[str, Any] = {"kind": "upload", "prompt": prompt[:300], "accept": ",".join(accept),
                               "multiple": bool(a.get("multiple"))}
    if a.get("field"):
        payload["field"] = _need(ctx, a["field"]).name
    if ctx.guide and ctx.guide.config.privacy_note:
        payload["privacy"] = ctx.guide.config.privacy_note
    ctx.pending_interaction = payload
    return ""


def _t_review_form(a: dict, ctx: ToolCtx) -> str:
    if _waiting(ctx):
        raise ToolError(WAITING)
    mode = a.get("mode") if a.get("mode") in ("status", "submit") else "status"
    ctx.pending_interaction = review.build(ctx, mode, a.get("warnings"), a.get("fixes"))
    return ""


def _t_confirm_action(a: dict, ctx: ToolCtx) -> str:
    if _waiting(ctx):
        raise ToolError(WAITING)
    title, message = str(a.get("title") or "").strip(), str(a.get("message") or "").strip()
    if not title or not message:
        raise ToolError("title and message must not be empty")
    ctx.pending_interaction = {"kind": "confirm", "title": title[:120], "message": message[:600],
                               "confirm_label": str(a.get("confirm_label") or "").strip()[:40],
                               "danger": bool(a.get("danger"))}
    details = [{"label": str(d["label"]).strip()[:40], "value": str(d["value"]).strip()[:80]}
               for d in a.get("details") or [] if isinstance(d, dict) and d.get("label") and d.get("value") is not None]
    if details:
        ctx.pending_interaction["details"] = details[:6]
    if str(a.get("consequence") or "").strip():
        ctx.pending_interaction["consequence"] = str(a["consequence"]).strip()[:200]
    return ""


def _t_propose_changes(a: dict, ctx: ToolCtx) -> str:
    if _waiting(ctx):
        raise ToolError(WAITING)
    changes = a.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ToolError("INVALID_JSON: changes must be a non-empty list")
    ok, errors, later = [], [], []
    for ch in changes:
        try:
            if not isinstance(ch, dict) or "name" not in ch or "value" not in ch:
                raise ToolError("each item must be {name, value}")
            n = _need(ctx, ch["name"])
            e = ctx.ov[n.name]
            if not n.is_field:
                raise ToolError(f"{n.name} is a container")
            if not e.visible:
                raise ToolError(f"{n.name} is hidden")
            if (n.role in CHOICE and not e.readonly and vals._codec(e.spec) is None
                    and (e.disabled or not e.options or not vals.find_option(e.options, ch["value"]))):
                later.append((n, e, ch))   # options appear once other fields are set: applied after them
                continue
            if e.disabled:
                raise ToolError(f"{n.name} is disabled (⊘): {disabled_reason(ctx.ov, ctx.deps, n.name)}")
            if e.readonly:
                raise ToolError(f"{n.name} is read-only, computed by the form")
            val = _norm_value(ctx, n.name, ch["value"])
            # card text for the user: language-neutral; `value` is in the form's own format
            ok.append({"name": n.name, "label": e.label or n.name, "kind": n.role,
                       "value": form_value(ctx, n.name, val),
                       "display": vals.display(val), **previous_of(ctx, n.name),
                       "reason": ch.get("reason", ""), "reveal": reveal_chain(ctx, n.name),
                       **_row_extras(ctx, n, e, ch, val)})
        except ToolError as err:
            errors.append(str(err))
    if ok:
        after = [x["name"] for x in ok]
        for n, e, ch in later:   # a dependent choice: the client looks the option up after applying the rest
            ok.append({"name": n.name, "label": e.label or n.name, "kind": n.role, "value": None, "deferred": True,
                       "lookup": str(ch["value"]), "display": vals.display(ch["value"]), "after": after,
                       "shape": (e.spec.shape if e.spec else None) or "option",
                       **previous_of(ctx, n.name), "reason": ch.get("reason", ""),
                       "reveal": reveal_chain(ctx, n.name)})
    else:
        for n, e, ch in later:
            if e.disabled:
                errors.append(f"{n.name} is disabled (⊘): {disabled_reason(ctx.ov, ctx.deps, n.name)}")
            elif not e.options:
                errors.append(f"{n.name} has no options right now (they probably depend on another field)")
            else:
                try:
                    _choice(e, n.name, ch["value"])
                except ToolError as err:
                    errors.append(str(err))
    if errors and not ok:
        raise ToolError("no change passed validation:\n" + "\n".join(errors))
    x = ctx.last_extraction
    if x and ctx.can("set.document") and any(c.get("confidence") for c in ok):
        ctx.pending_source = {"kind": "document", "title": x.get("title") or "", "attachment_id": x.get("attachment_id"),
                              "found": len(x.get("values") or {})}
    ctx.pending_changes = ok
    return "\n".join(errors)  # errors for some fields; the valid ones go to confirmation


# ---------------------------------------------------------------- delegated (separate model calls)


def _row_extras(ctx: ToolCtx, n: Any, e: Any, ch: dict, val: Any) -> dict:
    """What a card row carries besides the value: a consent, a soft issue, the document confidence."""
    out: dict[str, Any] = {}
    consent = ctx.pack.consents.get(n.name) if ctx.pack else None
    if n.role == "bool" and (consent is not None or e.props.get("consent")) and ctx.can("set.consent"):
        consent = consent or {}
        doc = consent.get("doc") or e.props.get("consent_doc")
        out.update(consent=True, required=bool(consent.get("required", e.required)),
                   **({"doc": doc} if isinstance(doc, dict) else {}))
    issue = str(ch.get("issue") or "").strip()
    if issue and ctx.can("set.issues"):
        out["issue"] = {"severity": "warning", "message": issue[:160]}
    x = ctx.last_extraction
    if x and ctx.can("set.document"):
        got = (x.get("values") or {}).get(n.name)
        if got and _same_value(got[0], val):
            out["confidence"] = got[1]
    return out


def _same_value(a: Any, b: Any) -> bool:
    norm = lambda v: re.sub(r"\s+", " ", str(v.get("id") if isinstance(v, dict) else v)).strip().casefold()  # noqa: E731
    return norm(a) == norm(b)


def _t_use_skill(a: dict, ctx: ToolCtx) -> str:
    skill = ctx.guide.skills.get(str(a["name"]), ctx.pack.form_id) if ctx.guide else None
    if not skill:
        raise ToolError(f"no skill {a['name']!r} for this form")
    tools = f"\nTools of this skill: {', '.join(t.name for t in skill.tools)}" if skill.tools else ""
    return f"Skill {skill.name}:\n{skill.instructions}{tools}"


async def _ta_ask_documents(a: dict, ctx: ToolCtx) -> str:
    if not ctx.pack.kb_documents or not ctx.guide:
        return "This form has no business documents. Say you do not know rather than guessing."

    def step(tool: str, args: Any) -> None:
        if ctx.emit:
            ctx.emit({"kind": "tool", "name": f"docs.{tool}", "input": args})

    try:
        from ..knowledge import research   # needs the `research` extra (deepagents)

        answer = await research.ask_documents(ctx.guide.knowledge, ctx.pack.form_id, ctx.pack.title,
                                              str(a["question"]), ctx.guide.models.research, step)
        items = research.parse_sources(answer)
        if items:
            ctx.turn_sources = [*(ctx.turn_sources or []), *[i for i in items if i not in (ctx.turn_sources or [])]][:6]
            if ctx.emit and ctx.can("sources"):
                ctx.emit({"kind": "sources", "items": items})
        return answer
    except Exception as e:  # noqa: BLE001 — a failed lookup must not break the turn
        raise ToolError(f"document research failed: {type(e).__name__}: {e}") from None


async def _ta_extract_from_attachment(a: dict, ctx: ToolCtx) -> str:
    found = ctx.guide.attachments.load(ctx.thread_id, str(a["attachment_id"])) if ctx.guide else None
    if not found:
        raise ToolError(f"no attachment {a['attachment_id']!r} in this conversation")
    filename, data = found
    names = att.candidate_fields(ctx.ov, a.get("fields"), a.get("container"))
    if not names:
        raise ToolError("no candidate fields; pass field names or a container")
    try:
        x = await att.extract(ctx.guide.models.extract, ctx.ov, filename, data, names)
    except Exception as e:  # noqa: BLE001
        raise ToolError(f"extraction failed: {type(e).__name__}: {e}") from None
    ctx.last_extraction = {"title": x.document_type or filename, "attachment_id": str(a["attachment_id"]),
                           "values": {f.field: [f.value, f.confidence] for f in x.fields}}
    return att.describe(ctx.ov, filename, x)
