"""FormGuide: the entry point. Holds the configured models, registries and stores,
and the LangGraph graph. Transport-agnostic: `run()` yields AG-UI-shaped events;
`formguide.server.create_router()` exposes it over HTTP/SSE if you use FastAPI.

    guide = FormGuide(load_config("formguide.yaml"))
    info = guide.register_form(jsx, form_id="loan_application", domain=optional_pack)
    async for event in guide.run(thread_id, message="Where do I enter my tax id?",
                                 state={"config": cfg, "jsx_hash": info["jsx_hash"], "form_id": "loan_application"}):
        ...
    async for event in guide.run(thread_id, resume={"accepted": True, "config": new_cfg}):
        ...
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from langchain_core.messages import messages_to_dict
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .agent.graph import build_graph
from .agent.actions import parse_config as parse_actions, resolve as resolve_actions
from .attachments.extract import AttachmentStore
from .otel import setup as otel_setup
from .config import GuideConfig
from .domain.packs import DomainPackRegistry, starters_of, validate_pack
from .form.layout import LayoutIndex, jsx_hash
from .form.overlay import DepStore
from .knowledge import compile as kb_compile
from .knowledge.base import KnowledgeBase
from .prefill import prefill_instruction, suggest_prefill
from .skills import SkillRegistry
from .form.values import value_warnings
from .agent.interaction import read_answer, read_confirm, read_decision, read_edits, read_review, read_upload
from .stats import RunStats, activate, deactivate
from .suggestions import suggest

stats_log = logging.getLogger("formguide.stats")
from .transcript import FileTranscriptStore, check_thread_id, new_entry, pending_card


def _loads(s: str) -> Any:
    try:
        return json.loads(s) if s else {}
    except ValueError:
        return s


class FormGuide:
    def __init__(self, config: GuideConfig | None = None):
        cfg = config or GuideConfig()
        self.config = cfg
        self._turns: dict[str, asyncio.Task] = {}   # thread id -> its running turn (see run_detached)
        self.models = cfg.models.resolve()
        from .models import build_model
        self.models.memory = build_model(cfg.memory.model) if cfg.memory.model else self.models.research
        self._recent: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))   # recent run stats per thread
        # tracer handlers, built once: factories are called, ready handlers are used as they are
        self._callbacks = [f if hasattr(f, "on_llm_start") or not callable(f) else f() for f in cfg.tracing.callbacks]
        self.otel = otel_setup(cfg.tracing.otel)   # OpenTelemetry tracer, or None (see otel.py)
        sg = cfg.suggestions
        self.suggestions_model = (build_model(sg.model) if sg.model else self.models.memory) if sg.enabled else None
        from .models import missing_keys
        m = self.models
        no_key: dict[str, list[str]] = {}
        for role, env in missing_keys({"agent": m.agent, "research": m.research, "compile": m.compile,
                                       "extract": m.extract, "memory": m.memory,
                                       "suggestions": self.suggestions_model}).items():
            no_key.setdefault(env, []).append(role)
        for env, roles in no_key.items():
            logging.getLogger("formguide").warning(
                "no API key for the %s model%s: set %s (until then every call fails with a connection error)",
                ", ".join(roles), "s" if len(roles) > 1 else "", env)
        self.data_dir = Path(cfg.data_dir)
        self.packs = cfg.domain_packs or DomainPackRegistry()
        self.knowledge = cfg.knowledge or KnowledgeBase(self.data_dir / "kb")
        self.packs.knowledge = self.knowledge
        self.skills = cfg.skills or SkillRegistry()
        self.attachments = cfg.attachments or AttachmentStore(self.data_dir / "attachments")
        from .transcribe import Transcriber, TranscriptionConfig
        tc = cfg.transcription
        if tc is True:
            tc = TranscriptionConfig()
        self.transcriber = Transcriber(tc) if tc else None   # server-side dictation, see transcribe.py
        self.checkpointer = cfg.checkpointer or InMemorySaver()
        self.transcripts = cfg.transcripts or FileTranscriptStore(self.data_dir / "transcripts")
        self.max_tool_rounds = cfg.max_tool_rounds
        self._tools = list(cfg.tools)
        self._layouts: dict[str, LayoutIndex] = {}
        self._deps: dict[str, DepStore] = {}
        self.graph = build_graph(self)

    # ------------------------------------------------------------------ forms
    def warm_up(self) -> None:
        """Load what the first request would otherwise wait for, in the background (the Whisper model).
        create_app calls it at startup; call it yourself when you mount the router on your own app."""
        if self.transcriber:
            self.transcriber.warm_up()

    def register_form(self, jsx: str, form_id: str | None = None, domain: dict[str, Any] | None = None,
                      config: dict[str, Any] | None = None) -> dict:
        """Parse and cache the layout (once per JSX); optionally register a domain pack shipped with the form.

        With a sample `config` ({props, state}) the warnings also say where values or options cannot be
        read with the configured field specs (components.fields), and what to set."""
        h = jsx_hash(jsx)
        if h not in self._layouts:
            self._layouts[h] = LayoutIndex(jsx, self.config.components)
            path = self._layout_path(h)
            if not path.exists():   # kept on disk so clients keep working after a server restart
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(jsx, encoding="utf-8")
        lay = self._layouts[h]
        warnings = list(lay.warnings)
        source = None
        if form_id:
            if domain:
                self.packs.register(form_id, domain)
            pack = self.packs.get(form_id)
            source = pack.source
            warnings += validate_pack(pack, set(lay.nodes))
        if config:
            warnings += value_warnings(lay, config)
        return {"jsx_hash": h, "nodes": len(lay.nodes), "domain_pack": source, "warnings": warnings}

    def _layout_path(self, h: str) -> Path:
        return self.data_dir / "layouts" / f"{h}.jsx"

    def layout(self, h: str) -> LayoutIndex | None:
        if h not in self._layouts and h.isalnum():
            path = self._layout_path(h)
            if path.is_file():
                self._layouts[h] = LayoutIndex(path.read_text(encoding="utf-8"), self.config.components)
        return self._layouts.get(h)

    def deps(self, h: str) -> DepStore:
        if h not in self._deps:
            path = self.data_dir / "deps" / f"{h}.json" if self.config.learn_dependencies else None
            self._deps[h] = DepStore(path)
        return self._deps[h]

    def actions_for(self, form_id: str, caps: frozenset[str] | None) -> frozenset[str]:
        """The agent actions on for this form and client (see agent/actions.py)."""
        return resolve_actions(parse_actions(self.config.actions), caps=caps,
                               has_documents=bool(self.knowledge.documents_for(form_id or "")),
                               attachments=self.config.attachments_enabled)

    def tools_for(self, form_id: str) -> list[BaseTool]:
        return self._tools + self.skills.tools_for(form_id)

    # ------------------------------------------------------------------ chat
    async def run(self, thread_id: str, *, message: str | None = None, state: dict[str, Any] | None = None,
                  resume: dict[str, Any] | None = None, run_id: str | None = None,
                  client_tools: list[dict] | None = None, tool_results: dict[str, str] | None = None,
                  prefill: dict[str, Any] | None = None, capabilities: list[str] | None = None,
                  trace_context: dict[str, str] | None = None) -> AsyncIterator[dict]:
        """One turn, as AG-UI events (plain dicts with the protocol's camelCase keys).

        - a new user message: `message` + `state` = {config, jsx_hash, form_id, ui?, attachments?};
        - a resume after a field-change card: `resume` = {accepted, config?, ui?, names?, comment?};
        - a resume after a question card: `resume` = {answer: {ids?, text?}} ({accepted: False} = skipped);
        - a resume after an upload request: `resume` = {attachment_ids} (none = skipped);
        - a resume after a confirmation: `resume` = {accepted};
        - a continuation after frontend tools ran: `tool_results` = {tool_call_id: content} + `state`;
        - a prefilled start: `prefill` = {data?, text?, attachment_ids?} + `state` (see suggest_prefill).

        `client_tools` are the frontend tools the client declared ([{name, description, parameters}]).
        `capabilities` are the cards and variants the client renders (see agent/actions.py); None = all.
        `trace_context`: the caller's W3C trace headers ({traceparent, tracestate}); with OpenTelemetry on,
        the turn's span joins that trace (see otel.py).
        Everything the user sees is also recorded in the thread's display transcript (see transcript.py)."""
        check_thread_id(thread_id)
        tx = self.transcripts
        entries = tx.list(thread_id)
        card = pending_card(entries)
        if resume is not None:
            if card and card["kind"] == "question":
                got, _ = read_answer(card, resume)
                applied = bool(got and (got.get("ids") or got.get("text")) and card.get("applies")
                               and resume.get("config"))
                tx.update(thread_id, card["id"], status="answered" if got else "dismissed",
                          **({"answer": got} if got else {}), **({"applied": True} if applied else {}))
            elif card and card["kind"] == "upload":
                files = read_upload(resume, lambda i: (self.attachments.load(thread_id, i) or (None,))[0])
                tx.update(thread_id, card["id"], status="answered" if files else "dismissed",
                          **({"files": files} if files else {}))
            elif card and card["kind"] == "confirm":
                tx.update(thread_id, card["id"], status="accepted" if read_confirm(resume) else "rejected")
            elif card and card["kind"] == "review":
                action, det = read_review(resume)
                tx.update(thread_id, card["id"], status="dismissed" if action == "closed" else "answered",
                          action=action, **det)
            elif card:
                applied, declined = read_decision(card.get("changes") or [], resume)
                status = "rejected" if not applied else "partial" if declined else "accepted"
                edited = read_edits(card.get("changes") or [], resume, applied)
                tx.update(thread_id, card["id"], status=status, **({"names": applied} if declined else {}),
                          **({"edited": edited} if edited else {}))
        else:
            if card:   # a new message closes an unanswered card (the graph does the same)
                tx.update(thread_id, card["id"], status="dismissed")
            for e in entries:   # results of frontend tools
                if e["kind"] == "tool" and e.get("call_id") in (tool_results or {}):
                    tx.update(thread_id, e["id"], result=tool_results[e["call_id"]])
            if message:
                files = [a.get("filename") for a in (state or {}).get("attachments") or []]
                tx.append(thread_id, new_entry("user", text=message, files=files))
            elif prefill:
                tx.append(thread_id, new_entry("notice", text="The form was prefilled from data the app already has."))
        mode = self.config.interrupt_mode
        run_id = run_id or str(uuid.uuid4())
        stats = RunStats(run_id, thread_id)
        if self.otel is not None:
            stats.span = self.otel.turn(thread_id=thread_id, run_id=run_id,
                                        form_id=(state or {}).get("form_id") or "", carrier=trace_context)
        stop = "answer"
        open_calls: set[str] = set()   # tool calls without a result: frontend tools
        token = activate(stats)   # the graph's nodes record into it (see stats.py)
        try:
            async for ev in self._events(thread_id, mode, stats, tx, message=message, state=state, resume=resume,
                                         run_id=run_id, client_tools=client_tools, tool_results=tool_results,
                                         prefill=prefill, capabilities=capabilities):
                if stats.span is not None:
                    stop = _track_stop(ev, stats.span, stop, open_calls)
                yield ev
        finally:
            deactivate(token)
            if stats.span is not None:
                if stop == "answer" and open_calls:
                    stop = "frontend_tool"
                e = stats.as_event()
                stats.span.end(stop, {"formguide.total_ms": e["total_ms"], "formguide.ttft_ms": e["ttft_ms"],
                                      "gen_ai.usage.input_tokens": e["tokens"]["input"],
                                      "gen_ai.usage.output_tokens": e["tokens"]["output"]})

    async def _events(self, thread_id: str, mode: str, stats: RunStats, tx: Any, *, message: str | None,
                      state: dict[str, Any] | None, resume: dict[str, Any] | None, run_id: str,
                      client_tools: list[dict] | None, tool_results: dict[str, str] | None,
                      prefill: dict[str, Any] | None, capabilities: list[str] | None = None) -> AsyncIterator[dict]:
        """The run's AG-UI events, with the transcript kept in step (the body of run())."""
        texts: dict[str, str] = {}
        calls: dict[str, dict] = {}
        interrupts: list[dict] = []
        said: list[str] = []          # this run's answer, for quick replies
        held_sources: list[dict] = [] # CUSTOM sources events, sent once before RUN_FINISHED
        context = ""                  # what the model saw of the form, for quick replies
        async for ev in self._run(thread_id, message=message, state=state, resume=resume, run_id=run_id,
                                  client_tools=client_tools, tool_results=tool_results, prefill=prefill,
                                  stats=stats, capabilities=capabilities):
            t, name = ev["type"], ev.get("name")
            if t == "TEXT_MESSAGE_CONTENT":
                texts[ev["messageId"]] = texts.get(ev["messageId"], "") + ev["delta"]
            elif t == "TEXT_MESSAGE_END" and texts.get(ev["messageId"], "").strip():
                said.append(texts[ev["messageId"]])
                tx.append(thread_id, new_entry("assistant", text=texts.pop(ev["messageId"])))
            elif name == "agent_context":
                context = (ev.get("value") or {}).get("text") or ""
            elif t == "RUN_ERROR":
                tx.append(thread_id, new_entry("error", text=ev["message"]))
            elif t == "TOOL_CALL_START":
                calls[ev["toolCallId"]] = {"name": ev["toolCallName"], "args": ""}
            elif t == "TOOL_CALL_ARGS":
                calls[ev["toolCallId"]]["args"] += ev["delta"]
            elif t == "TOOL_CALL_END":
                c = calls[ev["toolCallId"]]
                c["entry"] = tx.append(thread_id, new_entry("tool", call_id=ev["toolCallId"], name=c["name"],
                                                            input=_loads(c["args"])))
            elif t == "TOOL_CALL_RESULT" and ev["toolCallId"] in calls:
                tx.update(thread_id, calls[ev["toolCallId"]]["entry"]["id"], result=ev["content"])
            elif name == "memory_compacted":
                tx.append(thread_id, new_entry("notice", text="Earlier messages were summarized for the assistant; "
                                                              "the chat history is kept in full."))
            elif name == "sources":   # shown under the answer: held until the run ends
                held_sources.append(ev)
                continue
            elif name == "receipt":    # turns the confirmation card it follows into a receipt
                conf = next((e for e in reversed(tx.list(thread_id)) if e["kind"] == "confirm"), None)
                ev = {**ev, "value": {**ev["value"], **({"card_id": conf["id"]} if conf else {})}}
                if conf:
                    tx.update(thread_id, conf["id"], receipt=ev["value"])
            elif name == "on_interrupt" and ev["value"].get("type") in _CARD_KIND:
                q = {k: v for k, v in ev["value"].items() if k != "type"}
                entry = tx.append(thread_id, new_entry(_CARD_KIND[ev["value"]["type"]], **q, status="pending"))
                value = {**ev["value"], "card_id": entry["id"]}
                interrupts.append(value)
                if mode not in ("legacy", "both"):
                    continue
                ev = {**ev, "value": json.dumps(value, ensure_ascii=False)}
            elif name == "on_interrupt":
                src = {"source": ev["value"]["source"]} if ev["value"].get("source") else {}
                entry = tx.append(thread_id, new_entry("card", changes=ev["value"].get("changes", []), status="pending",
                                                       **src))
                value = {**ev["value"], "card_id": entry["id"]}
                interrupts.append(value)
                if mode not in ("legacy", "both"):
                    continue
                # ag-ui-langgraph convention (what CopilotKit's useLangGraphInterrupt reads): a JSON string
                ev = {**ev, "value": json.dumps(value, ensure_ascii=False)}
            elif t == "RUN_FINISHED" and interrupts and mode in ("structured", "both"):
                ev = {**ev, "outcome": {"type": "interrupt", "interrupts": [_outcome(v) for v in interrupts]}}
            if t in ("RUN_FINISHED", "RUN_ERROR") and held_sources:
                merged: list[dict] = []
                for h in held_sources:
                    merged += [i for i in h["value"]["items"] if i not in merged]
                held_sources.clear()
                if t == "RUN_FINISHED":
                    yield {"type": "CUSTOM", "name": "sources", "value": {"items": merged[:6]}}
            if t == "RUN_FINISHED" and not interrupts and said and self.suggestions_model is not None:
                user_text = message or next((e.get("text", "") for e in reversed(tx.list(thread_id))
                                             if e["kind"] == "user"), "")
                t_sug = RunStats.now()
                items = await suggest(self.suggestions_model, user_text=user_text, answer="\n".join(said),
                                      context=context, limit=self.config.suggestions.max,
                                      timeout=self.config.suggestions.timeout)
                stats.model_call(t_sug, None, None, kind="suggestions")
                if items:
                    applies = [self._suggested_changes(it.get("set"), resume, state) for it in items]
                    keep = [i for i, a in enumerate(applies) if a != "done"]   # already true in the form: no chip
                    items, applies = [items[i] for i in keep], [applies[i] for i in keep]
                if items:
                    yield {"type": "CUSTOM", "name": "suggestions",
                           "value": {"items": [it["text"] for it in items],
                                     **({"applies": applies} if any(applies) else {})}}
            if t in ("RUN_FINISHED", "RUN_ERROR"):   # the numbers go last, right before the terminal event
                summary = stats.as_event()
                self._recent[thread_id].append(summary)
                stats_log.info(json.dumps(summary, ensure_ascii=False))
                yield {"type": "CUSTOM", "name": "run_stats", "value": summary}
            yield ev

    def _suggested_changes(self, sets: dict | None, resume: dict[str, Any] | None,
                           state: dict[str, Any] | None) -> list[dict] | str | None:
        """A suggestion's {field: value} -> changes in the field-card shape, validated like a proposal.
        Invalid fields are dropped; None when nothing is left; "done" when the form already has every value."""
        if not sets or not state or not state.get("jsx_hash"):
            return None
        from .agent.tools import ToolCtx, ToolError, _norm_value, form_value, previous_of, reveal_chain
        from .form.overlay import Overlay
        from .form.values import display
        config = (resume or {}).get("config") or state.get("config")
        lay = self.layout(state["jsx_hash"])
        if lay is None or not isinstance(config, dict):
            return None
        pack = self.packs.get(state.get("form_id"))
        ov = Overlay(lay, config, pack.pii)
        ctx = ToolCtx(ov=ov, deps=self.deps(lay.jsx_hash), pack=pack, loc=None)  # type: ignore[arg-type]
        out: list[dict] = []
        same = 0
        for name, raw in sets.items():
            node = lay.nodes.get(str(name))
            if not node or not node.is_field:
                continue
            e = ov[node.name]
            if not e.editable or node.role == "file":
                continue
            try:
                val = _norm_value(ctx, node.name, raw)
                encoded = form_value(ctx, node.name, val)
                if e.filled and encoded == e.raw:
                    same += 1
                    continue
                out.append({"name": node.name, "label": e.label or node.name, "value": encoded,
                            "display": display(val), **previous_of(ctx, node.name),
                            "reveal": reveal_chain(ctx, node.name)})
            except ToolError:
                continue
        return out or ("done" if same else None)

    # ------------------------------------------------------------------ turns that outlive the connection
    RUN_WAIT_S = 120   # a new turn waits this long for the thread's running turn, then gives up

    async def run_detached(self, **kw: Any) -> AsyncIterator[dict]:
        """`run()` as a background task: the caller streams its events, and when the caller goes away
        (the tab closed, the page reloaded) the turn still finishes and records its result in the transcript.
        A turn for a thread whose turn is still running waits for it first (a RUN_ERROR after RUN_WAIT_S)."""
        thread_id = check_thread_id(kw["thread_id"])
        running = self._turns.get(thread_id)
        if running and not running.done():
            try:
                await asyncio.wait_for(asyncio.shield(running), self.RUN_WAIT_S)
            except asyncio.TimeoutError:
                yield {"type": "RUN_ERROR", "message": "The previous turn of this thread is still running.", "code": "busy"}
                return
            except BaseException:   # it failed or was stopped: the new turn may start
                pass
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def turn() -> None:
            try:
                async for ev in self.run(**kw):
                    queue.put_nowait(ev)
            finally:
                queue.put_nowait(None)
                if self._turns.get(thread_id) is task:
                    del self._turns[thread_id]

        task = asyncio.create_task(turn())
        task.add_done_callback(lambda t: t.cancelled() or t.exception())   # read, so nobody waiting is not a warning
        self._turns[thread_id] = task
        while (ev := await queue.get()) is not None:   # cancelled here when the client goes away; the turn goes on
            yield ev
        if not task.cancelled() and task.exception():
            raise task.exception()

    def running(self, thread_id: str) -> bool:
        t = self._turns.get(thread_id)
        return bool(t and not t.done())

    def stop(self, thread_id: str) -> bool:
        """Stop the thread's running turn (the chat's Stop: closing the connection no longer does it)."""
        t = self._turns.get(check_thread_id(thread_id))
        if not t or t.done():
            return False
        t.cancel()
        return True

    def thread(self, thread_id: str, form_id: str | None = None) -> dict[str, Any]:
        """What a client needs to restore a conversation: the transcript and the pending card, if any, and
        whether a turn is still running (the client checks back until it ends).
        For an empty thread of a form whose domain pack has `starters`, those opening messages too."""
        entries = self.transcripts.list(check_thread_id(thread_id))
        out = {"thread_id": thread_id, "transcript": entries, "pending_card": pending_card(entries),
               "running": self.running(thread_id)}
        if not entries and form_id:
            out["starters"] = starters_of(self.packs.get(form_id))
        return out

    def thread_messages(self, thread_id: str) -> list[dict[str, Any]]:
        """The transcript as AG-UI messages (for `agent.setMessages` / CopilotKit)."""
        out: list[dict[str, Any]] = []
        for e in self.transcripts.list(check_thread_id(thread_id)):
            if e["kind"] == "user":
                out.append({"id": e["id"], "role": "user", "content": e.get("text", "")})
            elif e["kind"] == "assistant":
                out.append({"id": e["id"], "role": "assistant", "content": e.get("text", "")})
            elif e["kind"] == "tool" and e.get("call_id"):
                out.append({"id": f"{e['id']}-call", "role": "assistant", "toolCalls": [{
                    "id": e["call_id"], "type": "function",
                    "function": {"name": e["name"], "arguments": json.dumps(e.get("input") or {}, ensure_ascii=False)}}]})
                if "result" in e:
                    out.append({"id": f"{e['id']}-result", "role": "tool", "toolCallId": e["call_id"],
                                "content": e["result"]})
        return out

    def feedback(self, thread_id: str, value: int, card_id: str | None = None) -> None:
        """A thumbs rating from the chat, kept in the thread's transcript."""
        if value not in (1, -1):
            raise ValueError("value must be 1 or -1")
        self.transcripts.append(check_thread_id(thread_id),
                                new_entry("feedback", value=value, **({"card_id": card_id} if card_id else {})))

    async def delete_thread(self, thread_id: str) -> None:
        """Forget a conversation: its transcript and the model's history."""
        self.transcripts.delete(check_thread_id(thread_id))
        if hasattr(self.checkpointer, "adelete_thread"):
            await self.checkpointer.adelete_thread(thread_id)

    async def _run(self, thread_id: str, *, message: str | None, state: dict[str, Any] | None,
                   resume: dict[str, Any] | None, run_id: str | None, client_tools: list[dict] | None = None,
                   tool_results: dict[str, str] | None = None, prefill: dict[str, Any] | None = None,
                   stats: RunStats | None = None, capabilities: list[str] | None = None) -> AsyncIterator[dict]:
        run_id = run_id or str(uuid.uuid4())
        stats = stats or RunStats(run_id, thread_id)
        form_id = (state or {}).get("form_id") or ""
        # Tracers (LangSmith via its environment variables, or config.tracing.callbacks) see every turn
        # under its conversation: the thread id and form are in the run's metadata and tags.
        cfg: dict[str, Any] = {
            "configurable": {"thread_id": thread_id},
            "run_name": "formguide turn",
            "tags": ["formguide", *([form_id] if form_id else []), *self.config.tracing.tags],
            "metadata": {"thread_id": thread_id, "run_id": run_id, "form_id": form_id,
                         "jsx_hash": (state or {}).get("jsx_hash") or ""},
        }
        if self._callbacks:
            cfg["callbacks"] = list(self._callbacks)
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
        opened: set[str] = set()
        error: str | None = None
        try:
            if resume is not None:
                inp: Any = Command(resume=resume, **({"update": {"capabilities": capabilities}}
                                                     if capabilities is not None else {}))
            else:
                st = state or {}
                if not self.layout(st.get("jsx_hash", "")):
                    raise KeyError("unknown jsx_hash: call register_form first")
                user_text = message or ""
                if prefill and not user_text:
                    user_text = await self._prefill_note(st, prefill, thread_id)
                inp = {"user_text": user_text, "config": st["config"], "jsx_hash": st["jsx_hash"],
                       "form_id": st.get("form_id"), "ui": st.get("ui") or {}, "thread_id": thread_id,
                       "attachments": st.get("attachments") or [], "client_results": tool_results or {}}
                if client_tools is not None:
                    inp["client_tools"] = client_tools
                inp["capabilities"] = capabilities if isinstance(capabilities, list) else None
            async for mode, chunk in self.graph.astream(inp, cfg, stream_mode=["custom", "updates"]):
                if mode == "updates":
                    for it in (chunk.get("__interrupt__") or ()) if isinstance(chunk, dict) else ():
                        yield {"type": "CUSTOM", "name": "on_interrupt", "value": it.value}
                    continue
                k = chunk.get("kind")
                if k == "text_start":
                    opened.add(chunk["id"])
                    yield {"type": "TEXT_MESSAGE_START", "messageId": chunk["id"], "role": "assistant"}
                elif k == "text_delta":
                    stats.first_token()
                    yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": chunk["id"], "delta": chunk["delta"]}
                elif k == "text_end":
                    opened.discard(chunk["id"])
                    yield {"type": "TEXT_MESSAGE_END", "messageId": chunk["id"]}
                elif k == "tool_call":
                    yield {"type": "TOOL_CALL_START", "toolCallId": chunk["id"], "toolCallName": chunk["name"]}
                    yield {"type": "TOOL_CALL_ARGS", "toolCallId": chunk["id"],
                           "delta": json.dumps(chunk["args"], ensure_ascii=False)}
                    yield {"type": "TOOL_CALL_END", "toolCallId": chunk["id"]}
                elif k == "tool_result":
                    yield {"type": "TOOL_CALL_RESULT", "messageId": f"{chunk['id']}-result", "toolCallId": chunk["id"],
                           "content": chunk["content"], "role": "tool"}
                elif k == "ui":
                    yield {"type": "CUSTOM", "name": "ui_directive", "value": chunk["directive"]}
                elif k == "note":
                    yield {"type": "CUSTOM", "name": "agent_note", "value": chunk["text"]}
                elif k == "sources":
                    yield {"type": "CUSTOM", "name": "sources", "value": {"items": chunk["items"]}}
                elif k == "receipt":
                    yield {"type": "CUSTOM", "name": "receipt", "value": chunk["receipt"]}
                elif k == "memory":
                    yield {"type": "CUSTOM", "name": "memory_compacted", "value": chunk}
                elif k == "tool" and chunk.get("parent_id"):   # a sub-step of a running tool
                    yield {"type": "CUSTOM", "name": "tool_progress",
                           "value": {"parent_id": chunk["parent_id"], "name": chunk.get("name"),
                                     "input": chunk.get("input")}}
                elif k == "context":
                    yield {"type": "CUSTOM", "name": "agent_context", "value": chunk}
                elif k == "error":
                    error = error or chunk["message"]
        except Exception as e:  # noqa: BLE001 — report instead of breaking the stream
            error = error or f"{type(e).__name__}: {e}"
        for mid in opened:    # never leave a text message open
            yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
        if error:             # RUN_ERROR is terminal: nothing follows it
            yield {"type": "RUN_ERROR", "message": error}
            return
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}

    # ------------------------------------------------------------------ prefill
    async def suggest_prefill(self, state: dict[str, Any], *, data: dict[str, Any] | None = None,
                              text: str | None = None, attachment_ids: list[str] | None = None,
                              thread_id: str | None = None) -> dict[str, Any]:
        """Validated values for the form from data the app already has (see prefill.py)."""
        return await suggest_prefill(self, state, data=data, text=text, attachment_ids=attachment_ids,
                                     thread_id=thread_id)

    async def _prefill_note(self, state: dict[str, Any], prefill: dict[str, Any], thread_id: str) -> str:
        res = await self.suggest_prefill(state, data=prefill.get("data"), text=prefill.get("text"),
                                         attachment_ids=prefill.get("attachment_ids"), thread_id=thread_id)
        return prefill_instruction(res, prefill.get("language"))

    def recent_runs(self, thread_id: str) -> list[dict]:
        """Stats of the thread's last runs (in memory, for the debug endpoint), oldest first."""
        return list(self._recent.get(thread_id, ()))

    async def history(self, thread_id: str) -> list[dict]:
        """The model's history (not the display transcript), for debugging."""
        st = await self.graph.aget_state({"configurable": {"thread_id": thread_id}})
        return messages_to_dict(st.values.get("messages", []))

    # ------------------------------------------------------------------ knowledge
    def add_document(self, namespace: str, filename: str, data: bytes) -> dict:
        return self.knowledge.add_document(namespace, filename, data)

    def delete_document(self, namespace: str, doc_id: str) -> bool:
        return self.knowledge.delete_document(namespace, doc_id)

    async def compile_knowledge(self, form_id: str, jsx: str, config: dict) -> dict:
        """Compile the documents in the form's scope into its domain pack."""
        self.register_form(jsx)
        return await kb_compile.compile_form(self.knowledge, form_id, self._layouts[jsx_hash(jsx)], config,
                                             self.models.compile)

    # ------------------------------------------------------------------ attachments
    def save_attachment(self, thread_id: str, filename: str, data: bytes) -> dict:
        return self.attachments.save(thread_id, filename, data)


def _track_stop(ev: dict, span: Any, stop: str, open_calls: set[str]) -> str:
    """What ended the run, for the turn span: an answer, a card (its type), a frontend tool or an error."""
    t = ev.get("type")
    if t == "RUN_ERROR":
        return "error"
    if t == "TOOL_CALL_END":
        open_calls.add(ev.get("toolCallId") or "")
    elif t == "TOOL_CALL_RESULT":
        open_calls.discard(ev.get("toolCallId") or "")
    elif t == "CUSTOM" and ev.get("name") == "on_interrupt":
        v = ev.get("value")
        v = json.loads(v) if isinstance(v, str) else (v or {})
        kind = str(v.get("type") or "set_fields")
        span.card(kind, str(v.get("card_id") or ""))
        return kind
    elif t == "RUN_FINISHED" and isinstance(ev.get("outcome"), dict):
        for it in ev["outcome"].get("interrupts") or []:
            kind = str((it.get("metadata") or {}).get("type") or it.get("reason") or "card")
            if stop == "answer":
                span.card(kind, str(it.get("id") or ""))
                stop = kind
    return stop


_CARD_KIND = {"ask": "question", "upload": "upload", "confirm": "confirm",   # interrupt type -> transcript kind
              "review": "review"}


def _outcome(v: dict[str, Any]) -> dict[str, Any]:
    """A card as an AG-UI 1.0 interrupt (RUN_FINISHED.outcome)."""
    meta = {k: x for k, x in v.items() if k not in ("type", "card_id")}
    if v.get("type") == "ask":
        return {"id": v["card_id"], "reason": "ask_user", "message": v["question"], "metadata": meta}
    if v.get("type") == "upload":
        return {"id": v["card_id"], "reason": "request_file", "message": v["prompt"], "metadata": meta}
    if v.get("type") == "confirm":
        return {"id": v["card_id"], "reason": "confirm_action", "message": v["title"], "metadata": meta}
    return {"id": v["card_id"], "reason": "confirm_field_changes", "message": "Confirm the proposed field values",
            "metadata": {"changes": v["changes"]}}
