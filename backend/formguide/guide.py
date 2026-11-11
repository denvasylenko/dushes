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

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from langchain_core.messages import messages_to_dict
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .agent.graph import build_graph
from .attachments.extract import AttachmentStore
from .config import GuideConfig
from .domain.packs import DomainPackRegistry, validate_pack
from .form.layout import LayoutIndex, jsx_hash
from .form.overlay import DepStore
from .knowledge import compile as kb_compile
from .knowledge.base import KnowledgeBase
from .prefill import prefill_instruction, suggest_prefill
from .skills import SkillRegistry
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
        self.models = cfg.models.resolve()
        from .models import build_model
        self.models.memory = build_model(cfg.memory.model) if cfg.memory.model else self.models.research
        self.data_dir = Path(cfg.data_dir)
        self.packs = cfg.domain_packs or DomainPackRegistry()
        self.knowledge = cfg.knowledge or KnowledgeBase(self.data_dir / "kb")
        self.packs.knowledge = self.knowledge
        self.skills = cfg.skills or SkillRegistry()
        self.attachments = cfg.attachments or AttachmentStore(self.data_dir / "attachments")
        self.checkpointer = cfg.checkpointer or InMemorySaver()
        self.transcripts = cfg.transcripts or FileTranscriptStore(self.data_dir / "transcripts")
        self.max_tool_rounds = cfg.max_tool_rounds
        self._tools = list(cfg.tools)
        self._layouts: dict[str, LayoutIndex] = {}
        self._deps: dict[str, DepStore] = {}
        self.graph = build_graph(self)

    # ------------------------------------------------------------------ forms
    def register_form(self, jsx: str, form_id: str | None = None, domain: dict[str, Any] | None = None) -> dict:
        """Parse and cache the layout (once per JSX); optionally register a domain pack shipped with the form."""
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

    def tools_for(self, form_id: str) -> list[BaseTool]:
        return self._tools + self.skills.tools_for(form_id)

    # ------------------------------------------------------------------ chat
    async def run(self, thread_id: str, *, message: str | None = None, state: dict[str, Any] | None = None,
                  resume: dict[str, Any] | None = None, run_id: str | None = None,
                  client_tools: list[dict] | None = None, tool_results: dict[str, str] | None = None,
                  prefill: dict[str, Any] | None = None) -> AsyncIterator[dict]:
        """One turn, as AG-UI events (plain dicts with the protocol's camelCase keys).

        - a new user message: `message` + `state` = {config, jsx_hash, form_id, ui?, attachments?};
        - a resume after a confirmation card: `resume` = {accepted, config?, ui?};
        - a continuation after frontend tools ran: `tool_results` = {tool_call_id: content} + `state`;
        - a prefilled start: `prefill` = {data?, text?, attachment_ids?} + `state` (see suggest_prefill).

        `client_tools` are the frontend tools the client declared ([{name, description, parameters}]).
        Everything the user sees is also recorded in the thread's display transcript (see transcript.py)."""
        check_thread_id(thread_id)
        tx = self.transcripts
        entries = tx.list(thread_id)
        card = pending_card(entries)
        if resume is not None:
            if card:
                tx.update(thread_id, card["id"], status="accepted" if resume.get("accepted") else "rejected")
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
        texts: dict[str, str] = {}
        calls: dict[str, dict] = {}
        interrupts: list[dict] = []
        async for ev in self._run(thread_id, message=message, state=state, resume=resume, run_id=run_id,
                                  client_tools=client_tools, tool_results=tool_results, prefill=prefill):
            t, name = ev["type"], ev.get("name")
            if t == "TEXT_MESSAGE_CONTENT":
                texts[ev["messageId"]] = texts.get(ev["messageId"], "") + ev["delta"]
            elif t == "TEXT_MESSAGE_END" and texts.get(ev["messageId"], "").strip():
                tx.append(thread_id, new_entry("assistant", text=texts.pop(ev["messageId"])))
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
            elif name == "on_interrupt":
                entry = tx.append(thread_id, new_entry("card", changes=ev["value"].get("changes", []), status="pending"))
                value = {**ev["value"], "card_id": entry["id"]}
                interrupts.append(value)
                if mode not in ("legacy", "both"):
                    continue
                # ag-ui-langgraph convention (what CopilotKit's useLangGraphInterrupt reads): a JSON string
                ev = {**ev, "value": json.dumps(value, ensure_ascii=False)}
            elif t == "RUN_FINISHED" and interrupts and mode in ("structured", "both"):
                ev = {**ev, "outcome": {"type": "interrupt", "interrupts": [
                    {"id": v["card_id"], "reason": "confirm_field_changes",
                     "message": "Confirm the proposed field values", "metadata": {"changes": v["changes"]}}
                    for v in interrupts]}}
            yield ev

    def thread(self, thread_id: str) -> dict[str, Any]:
        """What a client needs to restore a conversation: the transcript and the pending card, if any."""
        entries = self.transcripts.list(check_thread_id(thread_id))
        return {"thread_id": thread_id, "transcript": entries, "pending_card": pending_card(entries)}

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

    async def delete_thread(self, thread_id: str) -> None:
        """Forget a conversation: its transcript and the model's history."""
        self.transcripts.delete(check_thread_id(thread_id))
        if hasattr(self.checkpointer, "adelete_thread"):
            await self.checkpointer.adelete_thread(thread_id)

    async def _run(self, thread_id: str, *, message: str | None, state: dict[str, Any] | None,
                   resume: dict[str, Any] | None, run_id: str | None, client_tools: list[dict] | None = None,
                   tool_results: dict[str, str] | None = None, prefill: dict[str, Any] | None = None
                   ) -> AsyncIterator[dict]:
        cfg = {"configurable": {"thread_id": thread_id}}
        run_id = run_id or str(uuid.uuid4())
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
        opened: set[str] = set()
        error: str | None = None
        try:
            if resume is not None:
                inp: Any = Command(resume=resume)
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
                elif k == "memory":
                    yield {"type": "CUSTOM", "name": "memory_compacted", "value": chunk}
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
