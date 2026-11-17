"""LangGraph: every user message brings a fresh config in the state.

START → sync → compact → llm ─┬─(tool calls)→ tools ─┬→ llm
                    │                      ├─(propose_changes)→ confirm [interrupt] → llm
                    │                      └─(frontend tool calls)→ END (the client runs them;
                    │                         the next run brings the results, see sync)
                    ├─(no tool calls, nothing said)→ nudge → llm
                    └─(done)→ END

The model is any LangChain chat model with tool calling (configured per FormGuide).
History is stored as LangChain messages in the checkpointer.
"""
from __future__ import annotations
from ..cards import answer_text as card_answer_text

import json
import logging
import re
import unicodedata
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ..form.overlay import Overlay, compute_diff
from ..form.render import locate, render_changes, render_focus, render_outline
from ..models import cache_history, missing_key, system_message
from ..stats import RunStats, model_id
from ..stats import current as current_stats
from .memory import compact as compact_history
from .memory import new_turn_id
from .prompts import context_block, page_facts, sending, system_prompt
from .interaction import (answer_text, read_answer, read_field_answers, read_review, read_confirm, read_decision, read_edits, read_upload,
                          upload_text)
from .actions import capabilities as parse_caps
from .tools import card_schemas, BUILTIN, WAITING, ToolCtx, ToolError, run_tool, tool_schemas

if TYPE_CHECKING:
    from ..guide import FormGuide

log = logging.getLogger("formguide")

PREAMBLE_CHARS = 240  # shorter text right before a tool call may be an internal note
# The words start to flow early: once a second sentence begins (EARLY_MIN chars at least), or after EARLY_CHARS.
# A one-line "let me look" before a tool is still held back; a longer lead shown before tools is taken back
# (text_retract) when the model writes its answer again after them.
EARLY_CHARS = 160
EARLY_MIN = 40
_SECOND = re.compile(r"[.!?\u2026]['\")\u00bb\u201d]*\s+\S")   # a sentence ends and the next one starts


_BULLET = re.compile(r"^\s*(?:[-*+\u2022\u2013]|\d+[.)])\s+")
_SENTENCE = re.compile(r"(?<=[.!?\u2026])\s+")


def without_options(text: str, labels: list[str], question: str = "") -> str:
    """The words written before a choice card, without the list of its options: the card shows them. A bullet
    list that names options goes whole, a sentence that names two or more of them goes, and so does a line left
    only to introduce them. A sentence that names one option is a fact about it and stays. The text is returned
    as it was when it names fewer than two of the options."""
    names = sorted({x.strip().lower() for x in labels if isinstance(x, str) and len(x.strip()) > 1}, key=len, reverse=True)
    if not names:
        return text
    # the longest label first, each found label blanked: "Kids haircut" is one option, not also "Haircut"
    each = re.compile("|".join(rf"(?<!\w){re.escape(n)}(?:e?s)?(?!\w)" for n in names))

    def named(part: str) -> set[str]:
        plain = re.sub(r"[*_`]", "", part.lower())
        return {next(n for n in names if m.group(0).startswith(n)) for m in each.finditer(plain)}

    if len(named(text)) < 2:
        return text

    kept: list[str] = []

    def drop_intro() -> None:
        """The sentence that only introduced the list ("Here are the services:") goes with it."""
        i = len(kept) - 1
        while i >= 0 and not kept[i].strip():
            i -= 1
        if i >= 0 and kept[i].rstrip().endswith(":"):
            rest = _SENTENCE.split(kept[i].rstrip())[:-1]
            if rest:
                kept[i] = " ".join(rest)
            else:
                del kept[i:]

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if _BULLET.match(line):
            j = i
            while j < len(lines) and (_BULLET.match(lines[j]) or (lines[j].startswith((" ", "\t")) and lines[j].strip())):
                j += 1
            run = lines[i:j]
            items = [ln for ln in run if _BULLET.match(ln)]
            hits = sum(bool(named(ln)) for ln in items)
            if hits >= 2:   # the list is the card's options: all of it goes, the oddly worded item too
                drop_intro()
            else:
                kept.extend(run)
            i = j
            continue
        sentences = _SENTENCE.split(line)
        rest = [sent for sent in sentences if len(named(sent)) < 2]
        if len(rest) < len(sentences) and not rest:
            drop_intro()
        if rest or not line.strip():
            kept.append(" ".join(rest))
        i += 1
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    same = re.sub(r"\W+", " ", result).strip().lower() == re.sub(r"\W+", " ", question).strip().lower()
    return "" if same else result


def flows(held: str) -> bool:
    """The held text is clearly a reply: it may be shown now."""
    return len(held) >= EARLY_CHARS or (len(held) >= EARLY_MIN and bool(_SECOND.search(held)))


class AgentState(TypedDict, total=False):
    messages: list[BaseMessage]
    config: dict
    jsx_hash: str
    form_id: str
    ui: dict
    page: dict | None   # what the page the form sits on says: {title, description, sections: [{title, text}]}
    user_text: str
    thread_id: str
    attachments: list[dict]   # files attached to the current message: [{id, filename}]
    snapshot: dict
    version: int
    pending: dict | None
    stop_reason: str
    tool_round: int
    said: bool      # the user saw some text this turn
    lead_id: str | None   # a short lead shown before this turn's tools: taken back if the model writes again
    text_id: str | None   # the message id of the words the last model call put on the page (None: it wrote none)
    nudged: bool    # we already asked the model to reply with text
    limited: bool   # the turn used up max_tool_rounds: the model was asked to reply without more tools
    handed_back: str | None   # hand_back was called: the turn ends, Dushes answers
    system_prompt: str   # frozen for the thread: changing it would invalidate the model's earlier reasoning
    prompt_sent: str     # the instructions the model last got as <updated_instructions> (empty: none since compaction)
    memory: str          # summary of older turns after compaction (see memory.py)
    client_tools: list[dict]     # frontend tools declared by the client: [{name, description, parameters}]
    capabilities: list[str] | None   # what the client renders (forwardedProps.capabilities); None = all
    language: str | None             # the conversation's language (set, detected or named by the agent): cards use it
    last_extraction: dict | None     # the thread's last read document (values with confidence), for card sources
    turn_sources: list | None        # documents the researcher cited this turn (reset by each new message)
    client_results: dict         # results of frontend tool calls delivered by this run: {tool_call_id: content}
    pending_client: dict | None  # frontend tool calls awaiting results: {ids, server_results}


def _script(text: str) -> str | None:
    """Dominant writing system of a text (LATIN, CYRILLIC, GREEK, ...), or None."""
    counts: dict[str, int] = {}
    for ch in text:
        if ch.isalpha():
            try:
                s = unicodedata.name(ch).split(" ")[0]
            except ValueError:
                continue
            counts[s] = counts.get(s, 0) + 1
    return max(counts, key=counts.get) if counts else None


CARD_TOOLS = frozenset({"propose_changes", "ask_user", "request_file", "confirm_action"})


def is_note(text: str, state: dict) -> bool:
    """Short text right before a tool call is an internal note if the model has
    not done anything yet this turn, or if it is in a different script than the user."""
    if (state.get("tool_round") or 0) == 0:
        return True
    user, note = _script(state.get("user_text") or ""), _script(text)
    return bool(user and note and user != note)


def _approx_tokens(s: str) -> int:
    return round(len(s) / 3.2)


REASONING_BLOCKS = {"thinking", "redacted_thinking", "reasoning"}


def strip_reasoning(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Drop provider reasoning blocks from earlier assistant turns (text and tool calls stay)."""
    out = []
    for m in messages:
        if isinstance(m, AIMessage) and isinstance(m.content, list):
            content = [b for b in m.content if not (isinstance(b, dict) and b.get("type") in REASONING_BLOCKS)]
            m = m.model_copy(update={"content": content or ""})
        out.append(m)
    return out


def _is_reasoning_binding_error(e: Exception) -> bool:
    t = str(e).lower()
    return ("signature" in t and "thinking" in t) or "block is bound" in t


def _tool_messages(results: list[dict]) -> list[ToolMessage]:
    return [ToolMessage(content=r["content"], tool_call_id=r["id"], status="error" if r.get("error") else "success")
            for r in results]


NOT_EXECUTED = "The client did not run this tool (no result was returned)."


def client_tool_schemas(client_tools: list[dict] | None, taken: set[str]) -> list[dict]:
    """Frontend tools in OpenAI function format; names of built-in or server tools win."""
    out = []
    for t in client_tools or []:
        if t.get("name") and t["name"] not in taken:
            out.append({"type": "function", "function": {
                "name": t["name"], "description": t.get("description") or "",
                "parameters": t.get("parameters") or {"type": "object", "properties": {}}}})
    return out


def _unanswered(messages: list[BaseMessage]) -> list[dict]:
    """Error results for tool calls of the last assistant message that never got one (the turn was stopped or
    crashed in the middle). A provider refuses a history with a call and no result."""
    for i in range(len(messages) - 1, -1, -1):
        calls = getattr(messages[i], "tool_calls", None)
        if calls:
            done = {getattr(m, "tool_call_id", None) for m in messages[i + 1:]}
            return [{"id": c["id"], "content": "Not run: the previous turn ended before this step finished.",
                     "error": True} for c in calls if c.get("id") and c["id"] not in done]
        if getattr(messages[i], "type", "") == "human":
            break
    return []


def build_graph(guide: FormGuide):
    def server_tool_names(form_id: str | None) -> set[str]:
        return set(BUILTIN) | {t.name for t in guide.tools_for(form_id or "")}

    def client_names(state: AgentState) -> set[str]:
        taken = server_tool_names(state.get("form_id"))
        return {s["function"]["name"] for s in client_tool_schemas(state.get("client_tools"), taken)}

    def caps_of(state: AgentState) -> frozenset[str] | None:
        return parse_caps(state.get("capabilities"))

    def hidden(state: AgentState) -> bool:
        """The page shows only the chat: the person does not see this form (ui.form_visible is false)."""
        return (state.get("ui") or {}).get("form_visible") is False

    def actions_of(state: AgentState) -> frozenset[str]:
        on = guide.actions_for(state.get("form_id") or "", caps_of(state))
        if not can_act(state):
            on = on - {"confirm_action"}                       # nothing here to confirm: no tool sends or cancels
        return on - {"focus_field"} if hidden(state) else on   # nothing on the page to point at

    def can_act(state: AgentState) -> bool:
        """The run has a tool that does something outside the form (send, pay, cancel): the host's, a skill's
        or the page's. Without one the person sends the form themselves, with the form's own button."""
        return bool(guide.tools_for(state.get("form_id") or "")) or bool(client_names(state))

    def form_sent(state: AgentState) -> Any:
        """What the form says about being sent: `props[<root>].submitted` (true / false / {at, reference})."""
        root = (state.get("config") or {}).get("props", {}).get(guide.layout(state["jsx_hash"]).root or "")
        return root.get("submitted") if isinstance(root, dict) else None

    def ctx_for(state: AgentState) -> ToolCtx:
        lay = guide.layout(state["jsx_hash"])
        if lay is None:
            raise RuntimeError("layout is not registered: send the JSX to register_form / POST /layouts first")
        pack = guide.packs.get(state.get("form_id"))
        ov = Overlay(lay, state["config"], pack.pii)
        return ToolCtx(ov=ov, deps=guide.deps(lay.jsx_hash), pack=pack, loc=locate(ov, state.get("ui")),
                       thread_id=state.get("thread_id") or "", guide=guide,
                       extra_tools={t.name: t for t in guide.tools_for(pack.form_id)},
                       confirm_tools=frozenset(guide.config.confirm_tools or ()),
                       actions=actions_of(state), caps=caps_of(state), cards=guide.cards, can_act=can_act(state),
                       last_extraction=state.get("last_extraction"), turn_sources=state.get("turn_sources"))

    # ------------------------------------------------------------------ nodes
    def sync(state: AgentState) -> dict:
        """Diff the incoming config against the previous one, build context, append the message."""
        w = get_stream_writer()
        ctx = ctx_for(state)
        v_prev = state.get("version") or 0
        version = v_prev + 1
        diff = compute_diff(ctx.ov, state.get("snapshot"))
        ctx.deps.observe(diff, ctx.ov)
        outline = render_outline(ctx.ov, ctx.loc, ctx.deps, ctx.pack, version)
        focus = render_focus(ctx.ov, ctx.loc, ctx.deps, ctx.pack)
        changes = render_changes(ctx.ov, diff, v_prev, version) if v_prev else "CHANGES: this is the first message"
        # The frontend sends the user's local time; fall back to the server clock.
        now = (state.get("ui") or {}).get("now") or datetime.now().strftime("%Y-%m-%d %A %H:%M")
        block = context_block(outline, focus, changes, now, hidden=hidden(state), page=page_facts(state.get("page")),
                              sending=sending(form_sent(state), can_act(state), hidden(state)))
        cfg_chars = len(json.dumps(state["config"], ensure_ascii=False))
        w({"kind": "context", "text": block,
           "stats": {"context_tokens": _approx_tokens(block), "config_tokens": round(cfg_chars / 3.2)}})

        new: list[BaseMessage] = []
        pending = state.get("pending")
        if pending:  # the user ignored the card or question and wrote a new message
            ignored = {"ask": "The user did not answer the question and sent a new message instead.",
                       "upload": "The user did not upload a file and sent a new message instead.",
                       "confirm": "The user did not confirm and sent a new message instead. Nothing was run.",
                       "review": "The user closed the review and sent a new message instead.",
                       }.get(pending.get("kind") or "",
                             "The user did not answer the card and sent a new message. Nothing was applied.")
            new += _tool_messages(pending["other_results"] + [{"id": pending["tool_call_id"], "content": ignored}])
        pending_client = state.get("pending_client")
        if pending_client:  # results of frontend tools, delivered by this run
            got = state.get("client_results") or {}
            new += _tool_messages(pending_client["server_results"] + [
                {"id": i, "content": got[i]} if i in got else {"id": i, "content": NOT_EXECUTED, "error": True}
                for i in pending_client["ids"]])
        new += _tool_messages(_unanswered([*(state.get("messages") or []), *new]))   # a turn that broke off mid-call
        content: list[dict[str, Any]] = []
        # The system prompt is frozen per thread (append-only history). If the form's knowledge
        # changed since (documents recompiled, skills edited), deliver it as an update here.
        current = system_prompt(ctx.pack, guide.skills.for_form(ctx.pack.form_id), actions=ctx.actions)
        frozen = state.get("system_prompt") or current
        sent = state.get("prompt_sent") or frozen
        if current != sent:   # once per change: the update stays in the history
            content.append({"type": "text", "text": "<updated_instructions>\nThe form's instructions changed during this "
                                                    "conversation. These replace the earlier ones:\n" + current
                                                    + "\n</updated_instructions>"})
        user_text = state.get("user_text") or ""
        if not user_text and pending_client:
            user_text = "[The client returned the results of your frontend tool calls above. Continue.]"
        content += [{"type": "text", "text": block}, {"type": "text", "text": user_text or "…"}]
        for a in state.get("attachments") or []:
            content.append({"type": "text", "text": f"[The user attached {a['filename']} (attachment_id={a['id']}). "
                                                    "Use extract_from_attachment to read it.]"})
        new.append(HumanMessage(content=content, id=new_turn_id()))
        return {
            "messages": [*(state.get("messages") or []), *new],
            "snapshot": ctx.ov.snapshot(), "version": version, "pending": None, "tool_round": 0,
            "said": False, "lead_id": None, "text_id": None, "nudged": False, "limited": False, "handed_back": None, "attachments": [], "system_prompt": frozen,
            "prompt_sent": current if current != frozen else "",
            "pending_client": None, "client_results": {}, "turn_sources": None,
        }

    async def compact(state: AgentState) -> dict:
        """Long chats: summarize older turns into a conversation memory (see memory.py)."""
        pack = guide.packs.get(state.get("form_id"))
        t_mem, meta = RunStats.now(), {}
        try:
            res = await compact_history(state["messages"], state.get("memory") or "", guide.models.memory,
                                        guide.config.memory, pack.title, meta)
        except Exception as e:  # noqa: BLE001 — a failed compaction must not block the turn
            log.warning("compaction failed: %s", e)
            return {}
        finally:
            stats = current_stats()
            if stats and "usage" in meta:   # the summary's model call is counted like any other
                stats.model_call(t_mem, None, meta["usage"], kind="memory", model=model_id(guide.models.memory))
        if not res:
            return {}
        history, memory = res
        get_stream_writer()({"kind": "memory", "memory": memory,
                             "dropped_messages": len(state["messages"]) - len(history)})
        return {"messages": history, "memory": memory, "prompt_sent": ""}   # an update may be summarized away

    async def llm(state: AgentState) -> dict:
        w = get_stream_writer()
        pack = guide.packs.get(state.get("form_id"))
        from .. import intent as _intent
        base = _intent.preset_model(state.get("thread_id"), state.get("messages")) or guide.models.agent   # a value the choice layer picked
        server = guide.tools_for(pack.form_id)
        actions = actions_of(state)
        model = base.bind_tools(tool_schemas(server, actions, frozenset(guide.config.confirm_tools or ()))
                                + card_schemas(guide.cards, caps_of(state))
                                + client_tool_schemas(state.get("client_tools"), server_tool_names(pack.form_id)))
        sys_text = state.get("system_prompt") or system_prompt(pack, guide.skills.for_form(pack.form_id),
                                                               actions=actions)
        history = state["messages"]
        cached = guide.config.prompt_cache != "off"   # see models.cache_history
        msg_id = str(uuid.uuid4())
        started = False
        held = ""
        shown = 0          # chars of this call on the page
        lead = state.get("lead_id")   # an earlier call's lead, still on the page
        calling = False
        full = None

        def flush() -> None:
            nonlocal started, held, shown, lead
            if not held:
                return
            if not started:
                if lead:   # the answer comes again after the tools: the lead written before them goes
                    w({"kind": "text_retract", "id": lead})
                    lead = None
                w({"kind": "text_start", "id": msg_id})
                started = True
            shown += len(held)
            w({"kind": "text_delta", "id": msg_id, "delta": held})
            held = ""

        stats = current_stats()
        t_call = RunStats.now()
        first_chunk: float | None = None

        async def stream(msgs: list[BaseMessage]):
            nonlocal full, calling, held, first_chunk
            async for chunk in model.astream(msgs):
                if first_chunk is None:
                    first_chunk = RunStats.now()
                full = chunk if full is None else full + chunk
                if chunk.tool_call_chunks and not calling:
                    calling = True
                    card = (chunk.tool_call_chunks[0].get("name") or "") in CARD_TOOLS   # its lead sentence is for the user
                    if not started and held.strip() and not card and is_note(held, state):
                        w({"kind": "note", "text": held.strip()})
                        held = ""
                    else:
                        flush()
                text = chunk.text
                if text and not calling:
                    held += text
                    if started or flows(held):
                        flush()
                elif text:
                    held += text
                    flush()

        stripped = False
        try:
            try:
                await stream([system_message(sys_text, base, cached), *cache_history(history, base, cached)])
            except Exception as e:  # noqa: BLE001
                if full is not None or not _is_reasoning_binding_error(e):
                    raise
                # The provider rejected earlier reasoning blocks (their context changed): drop them, retry once.
                log.warning("reasoning blocks rejected (%s); retrying without them", e)
                history, stripped = strip_reasoning(history), True
                await stream([system_message(sys_text, base, cached), *cache_history(history, base, cached)])
            flush()
        except Exception as e:  # noqa: BLE001 — provider errors vary; surface them in the chat
            if stats:
                stats.model_call(t_call, first_chunk, None, model=model_id(base))
            env = missing_key(base)
            if env:   # the SDK reports a missing key as "Connection error": say what is really wrong
                log.error("model call failed: no API key, set %s", env)
                w({"kind": "error", "message": f"model error: no API key (set {env} on the server)"})
                return {"stop_reason": "error"}
            log.exception("model call failed")
            w({"kind": "error", "message": f"model error: {type(e).__name__}: {e}"})
            return {"stop_reason": "error"}
        if started:
            w({"kind": "text_end", "id": msg_id})
        if full is None:
            return {"stop_reason": "end_turn", "said": bool(state.get("said"))}
        msg = AIMessage(content=full.content, tool_calls=full.tool_calls, id=full.id,
                        response_metadata=full.response_metadata, usage_metadata=full.usage_metadata)
        if stats:
            rm = full.response_metadata or {}
            stats.model_call(t_call, first_chunk, dict(full.usage_metadata or {}),
                             model=str(rm.get("model_name") or rm.get("model") or "") or model_id(base))
        meta = full.response_metadata or {}
        if meta.get("stop_reason") == "refusal" or meta.get("finish_reason") == "content_filter":
            w({"kind": "error", "message": "the model declined to answer this request"})
        log.info("llm round=%s tools=%s usage=%s", state.get("tool_round"),
                 [c["name"] for c in msg.tool_calls], msg.usage_metadata)
        # a short lead before tools (not a card's own sentence) may be taken back once the answer comes after them
        to_tools = bool(msg.tool_calls) and not any(c["name"] in CARD_TOOLS for c in msg.tool_calls)
        if started and to_tools and shown <= PREAMBLE_CHARS:
            lead = msg_id
        elif started:
            lead = None   # this call's words stay: an older lead is no longer the last thing said before an answer
        return {"messages": [*history, msg],
                "stop_reason": "tool_use" if msg.tool_calls else "end_turn",
                "said": bool(state.get("said")) or started, "lead_id": lead, "text_id": msg_id if started else None}

    def route_llm(state: AgentState) -> str:
        if state.get("stop_reason") != "tool_use":
            if state.get("stop_reason") == "end_turn" and not state.get("said") and not state.get("nudged"):
                return "nudge"
            return END
        if (state.get("tool_round") or 0) >= guide.max_tool_rounds:
            return END if state.get("limited") else "limit"   # never end silently in the middle of a task
        return "tools"

    def limit(state: AgentState) -> dict:
        """The turn used up its tool rounds: answer the open calls and ask for a reply in text."""
        log.warning("turn reached max_tool_rounds (%s); asking for a reply", guide.max_tool_rounds)
        last = state["messages"][-1]
        open_calls = [{"id": c["id"], "content": "Not run: this turn reached its step limit.", "error": True}
                      for c in getattr(last, "tool_calls", None) or []]
        return {"messages": [*state["messages"], *_tool_messages(open_calls), HumanMessage(
            content="[system] This turn reached its step limit. Do not call tools now: tell the user in one or two "
                    "sentences what is done and what you will do next when they reply.")], "limited": True}

    def nudge(state: AgentState) -> dict:
        """Safety net: the model ended the turn without saying anything to the user."""
        log.warning("turn ended without text; nudging")
        return {"messages": [*state["messages"], HumanMessage(
            content="[system] You did not reply to the user with text. Reply briefly.")], "nudged": True}

    async def tools(state: AgentState) -> dict:
        w = get_stream_writer()
        ctx = ctx_for(state)
        ctx.emit = w
        last = state["messages"][-1]
        frontend = client_names(state)
        calls = getattr(last, "tool_calls", None) or []
        waiting_tools = {"propose_changes", "ask_user", "request_file", "confirm_action", "review_form",
                         *ctx.confirm_tools, *(n for n, c in guide.cards.items() if c.wait)}
        has_card_call = any(c["name"] in waiting_tools for c in calls)
        results: list[dict] = []
        client_ids: list[str] = []
        pending_id = None
        partial_errors = ""
        for call in calls:
            w({"kind": "tool_call", "id": call["id"], "name": call["name"], "args": call.get("args") or {},
               "client": call["name"] in frontend})
            if call["name"] in frontend:
                if has_card_call:   # a card and a frontend tool cannot both wait for the client
                    r = {"id": call["id"], "content": "Not executed: call frontend tools in a separate step.",
                         "error": True}
                    results.append(r)
                    w({"kind": "tool_result", **r})
                else:
                    client_ids.append(call["id"])
                continue
            if call["name"] in ctx.confirm_tools:   # configured to need the user's confirmation first: hold it
                if ctx.pending_changes is None and ctx.pending_interaction is None:
                    args = call.get("args") or {}
                    shown = ", ".join(f"{k}: {v}" for k, v in args.items())[:400]
                    ctx.pending_interaction = {"kind": "confirm", "title": f"Run {call['name']}?",
                                               "message": shown or "No details.", "confirm_label": "",
                                               "danger": False, "tool": call["name"], "args": args,
                                               "held": True}
                    pending_id = call["id"]
                    continue
                r = {"id": call["id"], "content": WAITING, "error": True}
                results.append(r)
                w({"kind": "tool_result", **r})
                continue
            # sub-steps of a tool (e.g. the document researcher) carry the id of the call they belong to
            ctx.emit = (lambda cid: lambda d: w({**d, "parent_id": cid} if d.get("kind") == "tool" else d))(call["id"])
            before = (ctx.pending_changes, ctx.pending_interaction)
            stats, t_tool, failed = current_stats(), RunStats.now(), False
            try:
                out = await run_tool(call["name"], call.get("args"), ctx)
                if before == (None, None) and (ctx.pending_changes is not None or ctx.pending_interaction is not None):
                    pending_id = call["id"]
                    partial_errors = out
                    continue
                r = {"id": call["id"], "content": out or "ok"}
            except ToolError as e:
                r = {"id": call["id"], "content": str(e), "error": True}
                failed = True
            except Exception as e:  # noqa: BLE001 - a call never stays without a result: the model reads the failure
                log.exception("tool %s failed", call["name"])
                r = {"id": call["id"], "content": f"{call['name']} failed ({type(e).__name__}): check the arguments "
                                                  "or do it another way", "error": True}
                failed = True
            finally:
                if stats:
                    stats.tool_call(call["name"], t_tool, failed)
            results.append(r)
            w({"kind": "tool_result", **r})
        for d in ctx.ui_directives:
            w({"kind": "ui", "directive": d})
        upd: dict[str, Any] = {"tool_round": (state.get("tool_round") or 0) + 1}
        if ctx.handed_back:
            upd["handed_back"] = ctx.handed_back
            w({"kind": "hand_back", "reason": ctx.handed_back})
        if ctx.last_extraction is not state.get("last_extraction"):
            upd["last_extraction"] = ctx.last_extraction
        if ctx.turn_sources is not state.get("turn_sources"):
            upd["turn_sources"] = ctx.turn_sources
        if pending_id and ctx.pending_interaction is not None:
            pi = dict(ctx.pending_interaction)
            upd["pending"] = {"kind": pi.pop("kind"), "tool_call_id": pending_id, "payload": pi,
                              "other_results": results}
        elif pending_id:
            upd["pending"] = {"kind": "set_fields", "tool_call_id": pending_id, "changes": ctx.pending_changes,
                              "partial_errors": partial_errors, "other_results": results,
                              **({"source": ctx.pending_source} if ctx.pending_source else {})}
        elif client_ids:
            upd["pending_client"] = {"ids": client_ids, "server_results": results}
        if upd.get("pending") and upd["pending"].get("kind") == "ask" and state.get("text_id"):
            # the options are on the card: the words before it do not list them again
            pay = upd["pending"]["payload"]
            labels = [str(o.get("label") or "") for o in pay.get("options") or [] if isinstance(o, dict)]
            last = state["messages"][-1]
            said_now = last.content if isinstance(last.content, str) else "".join(
                b.get("text", "") for b in last.content if isinstance(b, dict) and b.get("type") == "text")
            short = without_options(said_now, labels, str(pay.get("question") or ""))
            if short != said_now:
                w({"kind": "text_retract", "id": state["text_id"]})
                if short:
                    again = str(uuid.uuid4())
                    w({"kind": "text_start", "id": again})
                    w({"kind": "text_delta", "id": again, "delta": short})
                    w({"kind": "text_end", "id": again})
        if upd.get("pending"):   # the card in the conversation's language, before it is shown or stored
            from ..language import conversation, localize
            lang = conversation(guide.config, ctx.ov[ctx.ov.layout.root].props if ctx.ov.layout.root else None,
                                None, ctx.language or state.get("language"))
            if lang and lang != state.get("language"):
                upd["language"] = lang
                w({"kind": "language", "lang": lang})
            await localize(upd["pending"], ctx.ov, lang, translator=guide.translator,
                           model=guide.translation_model if guide.config.translate_missing else None,
                           stats=current_stats())
        else:
            upd["messages"] = [*state["messages"], *_tool_messages(results)]
        return upd

    def route_tools(state: AgentState) -> str:
        if state.get("handed_back") and not state.get("pending"):
            return END   # Dushes answers this message (Dushes runs it next)
        if state.get("pending"):
            return "confirm"
        return END if state.get("pending_client") else "llm"

    async def confirm(state: AgentState) -> dict:
        """Human in the loop. The frontend shows a card and resumes the graph with the user's answer:
        a field-change card {accepted, config, names?, edited?}; a question {answer}; an upload request
        {attachment_ids}; a confirmation {accepted}. Field changes are applied by the frontend through the
        normal pipeline (the form backend rebuilds the config)."""
        p = state["pending"]
        # a card answer is the user's input: the turn's tool rounds start again (a chain of one-tap answers
        # is one turn, and it must not run out of rounds)
        upd: dict[str, Any] = {"pending": None, "tool_round": 0, "limited": False}
        kind = p.get("kind") or "set_fields"
        if kind != "set_fields":
            payload = p.get("payload") or p.get("question") or {}   # "question": threads from before kinds
            shown = {k: v for k, v in payload.items() if k != "held"}
            answer = interrupt({"type": kind, **shown})
            answer = answer if isinstance(answer, dict) else {"answer": answer}
            if kind == "ask" and payload.get("fields"):
                values, problems = read_field_answers(payload, answer)
                if not values or not answer.get("config"):
                    text = "The user skipped the question." if not values else (
                        "The user answered: " + "; ".join(f"{k} = {v}" for k, v in values.items())
                        + ". The values were not applied; propose them.")
                else:
                    new_cfg = answer["config"]
                    upd["config"] = new_cfg
                    ctx = ctx_for({**state, "config": new_cfg, "ui": answer.get("ui") or state.get("ui")})
                    diff = compute_diff(ctx.ov, state.get("snapshot"), agent_names=set(values))
                    ctx.deps.observe(diff, ctx.ov)
                    v = (state.get("version") or 0) + 1
                    upd.update(snapshot=ctx.ov.snapshot(), version=v)
                    refused = {k: str(ctx.ov[k].error) for k in values if ctx.ov[k].error}   # the form said no
                    kept = {k: val for k, val in values.items() if k not in refused}
                    text = ("The user filled: " + "; ".join(f"{ctx.ov[k].label or k} ({k}) = {val}"
                                                            for k, val in kept.items())
                            + ". Do not propose these fields again.\n" if kept else "") + render_changes(ctx.ov, diff, v - 1, v)
                    problems = [*problems, *[f"{ctx.ov[k].label or k}: {why}" for k, why in refused.items()]]
                if problems:
                    text += ("\nNot accepted, so not filled: " + "; ".join(problems) + ". Tell the user which value "
                             "was not accepted and why, and ask for it again.")
                    get_stream_writer()({"kind": "card_result", "status": "not_accepted",
                                         "reason": "; ".join(problems)[:300]})
            elif kind == "ask":
                got, why = read_answer(payload, answer)
                text = answer_text(got, why)
                if not got and why:   # an answer was given and could not be taken: the card must not look answered
                    get_stream_writer()({"kind": "card_result", "status": "not_accepted", "reason": why[:300]})
                refused = {str(k): str(e) for k, e in (answer.get("rejected") or {}).items() if e} \
                    if isinstance(answer.get("rejected"), dict) else {}
                if got and refused:   # the client tried the value on the form and the form said no: nothing was filled
                    name = payload.get("field") if payload.get("field") in refused else next(iter(refused))
                    text += (f". The form did not accept it for {name}: {refused[name][:300]}. The field is not filled: "
                             "tell the user why, in their words, and ask again. Do not say it is filled.")
                    get_stream_writer()({"kind": "card_result", "status": "not_accepted", "reason": refused[name][:300],
                                         "field": name})
                elif got and (got.get("ids") or got.get("text")) and payload.get("applies") and answer.get("config"):
                    # the client filled the field with the chosen option: like an accepted card
                    new_cfg = answer["config"]
                    upd["config"] = new_cfg
                    ctx = ctx_for({**state, "config": new_cfg, "ui": answer.get("ui") or state.get("ui")})
                    diff = compute_diff(ctx.ov, state.get("snapshot"), agent_names={payload["field"]})
                    ctx.deps.observe(diff, ctx.ov)
                    v = (state.get("version") or 0) + 1
                    upd.update(snapshot=ctx.ov.snapshot(), version=v)
                    label = ctx.ov[payload["field"]].label or payload["field"]
                    error = ctx.ov[payload["field"]].error
                    if error:   # the form refused the value: the field is not filled, and the card says so
                        text += (f". The form did not accept it for {label} ({payload['field']}): {error}. The field "
                                 "is not filled: tell the user why, in their words, and ask again.\n"
                                 + render_changes(ctx.ov, diff, v - 1, v))
                        get_stream_writer()({"kind": "card_result", "status": "not_accepted", "reason": str(error)[:300],
                                             "field": payload["field"]})
                    else:
                        text += (f". This filled the field {label} ({payload['field']}); do not propose it again.\n"
                                 + render_changes(ctx.ov, diff, v - 1, v))
            elif kind == "review":
                action, det = read_review(answer)
                if action == "fixed":
                    new_cfg = answer["config"]
                    upd["config"] = new_cfg
                    ctx = ctx_for({**state, "config": new_cfg, "ui": answer.get("ui") or state.get("ui")})
                    diff = compute_diff(ctx.ov, state.get("snapshot"), agent_names=set(det["names"]))
                    ctx.deps.observe(diff, ctx.ov)
                    v = (state.get("version") or 0) + 1
                    upd.update(snapshot=ctx.ov.snapshot(), version=v)
                    text = (f"The user applied the fixes for: {', '.join(det['names'])}. Do not propose them again.\n"
                            + render_changes(ctx.ov, diff, v - 1, v))
                elif action == "submit":
                    text = ("The user wants to send the form now. Ask with confirm_action before the tool that "
                            "submits it; if errors remain, say what blocks sending instead."
                            if can_act(state) else
                            "The user wants to send the form now. You have no tool that sends it: say in one "
                            "sentence what still blocks sending, or that it is ready and they send it with the "
                            "form's own send button. Do not say it was sent.")
                elif action == "continue":
                    text = ("The user wants to continue" + (f" with the section {det['section']}" if det["section"]
                                                            else "") + ": guide them to the next fields there.")
                else:
                    text = "The user closed the review."
            elif kind == "upload":
                tid = state.get("thread_id") or ""
                files = read_upload(answer, lambda i: (guide.attachments.load(tid, i) or (None,))[0])
                text = upload_text(files)
            elif kind == "blocks":   # a card from blocks: which button, which values
                spec = guide.cards.get(f"show_{payload.get('name')}")
                text = card_answer_text(spec, answer) if spec else "The user answered the card."
                chosen = next((it for b in payload.get("blocks") or [] if b.get("type") == "buttons"
                               for it in b.get("items") or [] if str(it.get("id")) == str(answer.get("action"))), None)
                filled = list((chosen or {}).get("fills") or {})
                if filled and answer.get("config"):   # the tap filled form fields: like an accepted card
                    new_cfg = answer["config"]
                    upd["config"] = new_cfg
                    ctx = ctx_for({**state, "config": new_cfg, "ui": answer.get("ui") or state.get("ui")})
                    diff = compute_diff(ctx.ov, state.get("snapshot"), agent_names=set(filled))
                    ctx.deps.observe(diff, ctx.ov)
                    v = (state.get("version") or 0) + 1
                    upd.update(snapshot=ctx.ov.snapshot(), version=v)
                    labels = ", ".join(f"{ctx.ov[n].label or n} ({n})" for n in filled)
                    text += (f" This filled {labels}; do not propose these fields again.\n"
                             + render_changes(ctx.ov, diff, v - 1, v))
            elif read_confirm(answer) and payload.get("held"):
                stats, t_tool, failed = current_stats(), RunStats.now(), False
                try:
                    held = ctx_for(state)
                    held.emit = get_stream_writer()
                    out = await run_tool(payload["tool"], payload.get("args"), held)
                    text = "The user confirmed. " + (out or "ok")
                except ToolError as e:
                    text = f"The user confirmed, but the tool failed: {e}"
                    failed = True
                except Exception as e:  # noqa: BLE001 - the held call gets its result too
                    log.exception("held tool %s failed", payload["tool"])
                    text = f"The user confirmed, but the tool failed ({type(e).__name__})."
                    failed = True
                if stats:
                    stats.tool_call(payload["tool"], t_tool, failed)
            elif payload.get("held"):
                text = "The user declined; the tool was not run."
            else:
                text = "The user confirmed." if read_confirm(answer) else "The user declined."
            if payload.get("held"):   # the held call's result reaches the client like any tool's
                get_stream_writer()({"kind": "tool_result", "id": p["tool_call_id"], "content": text})
            results = p["other_results"] + [{"id": p["tool_call_id"], "content": text}]
            upd["messages"] = [*state["messages"], *_tool_messages(results)]
            return upd
        answer = interrupt({"type": "set_fields", "changes": p["changes"],
                            **({"source": p["source"]} if p.get("source") else {})})
        answer = answer if isinstance(answer, dict) else {"accepted": bool(answer)}
        applied, declined = read_decision(p["changes"], answer)
        comment = f" Comment: {answer['comment']}" if answer.get("comment") else ""
        unticked = [c["name"] for c in p["changes"] if c.get("consent") and c["name"] in declined]
        consent_note = (f" Not ticked by the user: {', '.join(unticked)}. A consent is only the person's own tick: "
                        "do not set it. When it is required, say it is still needed; you may ask about it with a "
                        "question card for that field, and their answer fills it.") if unticked else ""
        if not applied:
            text = ("Nothing was applied." if unticked and len(unticked) == len(declined)
                    else "The user rejected the changes.") + consent_note + comment
        else:
            new_cfg = answer.get("config") or state["config"]
            upd["config"] = new_cfg
            ctx = ctx_for({**state, "config": new_cfg, "ui": answer.get("ui") or state.get("ui")})
            diff = compute_diff(ctx.ov, state.get("snapshot"), agent_names=set(applied))
            ctx.deps.observe(diff, ctx.ov)
            v = (state.get("version") or 0) + 1
            upd.update(snapshot=ctx.ov.snapshot(), version=v)
            head = ("The user confirmed; changes applied." if not declined else
                    f"The user applied: {', '.join(applied)}. Declined (not applied): {', '.join(declined)}."
                    + comment)
            edits = read_edits(p["changes"], answer, applied)
            if edits:
                head += " The user edited before applying: " + "; ".join(
                    f"{k} -> {json.dumps(v, ensure_ascii=False)}" for k, v in edits.items()) + "."
            head += consent_note
            text = head + "\n" + render_changes(ctx.ov, diff, v - 1, v)
        if p.get("partial_errors"):
            text += "\nFailed validation and were not proposed:\n" + p["partial_errors"]
        results = p["other_results"] + [{"id": p["tool_call_id"], "content": text}]
        upd["messages"] = [*state["messages"], *_tool_messages(results)]
        return upd

    g = StateGraph(AgentState)
    g.add_node("sync", sync)
    g.add_node("llm", llm)
    g.add_node("tools", tools)
    g.add_node("confirm", confirm)
    g.add_node("nudge", nudge)
    g.add_node("limit", limit)
    g.add_node("compact", compact)
    g.add_edge(START, "sync")
    g.add_edge("sync", "compact")
    g.add_edge("compact", "llm")
    g.add_conditional_edges("llm", route_llm, ["tools", "nudge", "limit", END])
    g.add_edge("nudge", "llm")
    g.add_edge("limit", "llm")
    g.add_conditional_edges("tools", route_tools, ["llm", "confirm", END])
    g.add_edge("confirm", "llm")
    return g.compile(checkpointer=guide.checkpointer)
