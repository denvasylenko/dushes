"""Agent tools. All are read-only except two with a UI side effect:

- focus_field     -> a UI directive for the frontend (open tabs/accordions, highlight);
- propose_changes -> validated, then goes to an interrupt (the user confirms).

Two tools delegate to separate model calls, so their inputs never enter the main context:
- ask_documents           -> the deep-agent researcher over the form's business documents;
- extract_from_attachment -> reads a file the user attached and returns field values.

`use_skill` loads a skill's instructions. Tools contributed by skills or by the
config (any LangChain BaseTool) run here too, after the built-in ones.

The agent cannot "write" the config: the config belongs to the form backend.
The frontend applies changes through the same path as user input.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from ..attachments import extract as att
from ..domain.packs import DomainPack
from ..knowledge import research

if TYPE_CHECKING:
    from ..guide import FormGuide
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
                       "confirms or rejects it. For dropdowns pass the option id. Dates: YYYY-MM-DD. "
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
                            "value": {"type": ["string", "number", "boolean"]},
                            "reason": {"type": "string"},
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


def tool_schemas(extra: list[BaseTool]) -> list[Any]:
    """Built-in tools in the provider-neutral (OpenAI function) format + extra LangChain tools."""
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}} for t in TOOLS] + list(extra)


@dataclass
class ToolCtx:
    ov: Overlay
    deps: DepStore
    pack: DomainPack
    loc: Location
    ui_directives: list[dict] = field(default_factory=list)
    pending_changes: list[dict] | None = None
    thread_id: str = ""
    emit: Callable[[dict], None] | None = None   # progress events for the UI
    guide: FormGuide | None = None               # access to models, knowledge, attachments, skills
    extra_tools: dict[str, BaseTool] = field(default_factory=dict)


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
    if name not in BUILTIN and name in ctx.extra_tools:
        try:
            out = await ctx.extra_tools[name].ainvoke(raw_args or {})
        except Exception as e:  # noqa: BLE001 — report tool failures to the model
            raise ToolError(f"{name} failed: {type(e).__name__}: {e}") from None
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
    if n.role != "select":
        raise ToolError(f"{n.name} is not a dropdown")
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

# Yes / no in several languages; Cyrillic words are escaped: \u0434\u0430 = "da" (ru), \u0442\u0430\u043a = "tak" (uk),
# \u043d\u0435\u0442 = "net" (ru), \u043d\u0456 = "ni" (uk).
_TRUE = {"true", "1", "yes", "y", "\u0434\u0430", "\u0442\u0430\u043a", "ja", "oui", "si", "s\u00ed"}
_FALSE = {"false", "0", "no", "n", "\u043d\u0435\u0442", "\u043d\u0456", "nein", "non"}


def _norm_value(ctx: ToolCtx, name: str, value: Any) -> Any:
    e = ctx.ov[name]
    role = e.node.role
    if role == "select":
        v = str(value).strip().lower()
        for o in e.options or []:
            if v in (str(o["id"]).lower(), o["name"].lower()):
                return {"id": o["id"], "name": o["name"]}
        avail = ", ".join(f"{o['id']}:{o['name']}" for o in (e.options or [])[:12]) or "the list is empty"
        raise ToolError(f"{name}: there is no option {value!r}. Available: {avail}")
    if role == "bool":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
        raise ToolError(f"{name}: true/false expected")
    if role == "date":
        s = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                pass
        raise ToolError(f"{name}: date expected as YYYY-MM-DD")
    if role == "number":
        s = re.sub(r"[\s_]", "", str(value)).replace(",", ".")
        try:
            float(s)
        except ValueError:
            raise ToolError(f"{name}: a number is expected") from None
        return s
    if role == "file":
        raise ToolError(f"{name}: only the user can upload a file. Show the field with focus_field.")
    return str(value)


def _t_propose_changes(a: dict, ctx: ToolCtx) -> str:
    if ctx.pending_changes is not None:
        raise ToolError("a proposal is already waiting for confirmation. One at a time.")
    changes = a.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ToolError("INVALID_JSON: changes must be a non-empty list")
    ok, errors = [], []
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
            if e.disabled:
                raise ToolError(f"{n.name} is disabled (⊘): {disabled_reason(ctx.ov, ctx.deps, n.name)}")
            if e.readonly:
                raise ToolError(f"{n.name} is read-only, computed by the form")
            val = _norm_value(ctx, n.name, ch["value"])
            # card text for the user: language-neutral
            shown = val["name"] if isinstance(val, dict) else ("✓" if val is True else "✗" if val is False else val)
            ok.append({"name": n.name, "label": e.label or n.name, "value": val,
                       "display": str(shown),
                       "reason": ch.get("reason", ""), "reveal": reveal_chain(ctx, n.name)})
        except ToolError as err:
            errors.append(str(err))
    if errors and not ok:
        raise ToolError("no change passed validation:\n" + "\n".join(errors))
    ctx.pending_changes = ok
    return "\n".join(errors)  # errors for some fields; the valid ones go to confirmation


# ---------------------------------------------------------------- delegated (separate model calls)


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
        return await research.ask_documents(ctx.guide.knowledge, ctx.pack.form_id, ctx.pack.title,
                                            str(a["question"]), ctx.guide.models.research, step)
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
    return att.describe(ctx.ov, filename, x)
