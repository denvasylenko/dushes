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
from .skills import SkillRegistry
from .transcript import FileTranscriptStore, check_thread_id, new_entry, pending_card


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

    def layout(self, h: str) -> LayoutIndex | None:
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
                  resume: dict[str, Any] | None = None, run_id: str | None = None) -> AsyncIterator[dict]:
        """One turn. Either a new user message (with state = {config, jsx_hash, form_id, ui?, attachments?})
        or a resume after a confirmation card ({accepted, config?, ui?}).

        Everything the user sees is also recorded in the thread's display transcript (see transcript.py)."""
        check_thread_id(thread_id)
        tx = self.transcripts
        card = pending_card(tx.list(thread_id))
        if resume is not None:
            if card:
                tx.update(thread_id, card["id"], status="accepted" if resume.get("accepted") else "rejected")
        else:
            if card:   # a new message closes an unanswered card (the graph does the same)
                tx.update(thread_id, card["id"], status="dismissed")
            files = [a.get("filename") for a in (state or {}).get("attachments") or []]
            tx.append(thread_id, new_entry("user", text=message or "", files=files))
        texts: dict[str, str] = {}
        async for ev in self._run(thread_id, message=message, state=state, resume=resume, run_id=run_id):
            t, name = ev["type"], ev.get("name")
            if t == "TEXT_MESSAGE_CONTENT":
                texts[ev["messageId"]] = texts.get(ev["messageId"], "") + ev["delta"]
            elif t == "TEXT_MESSAGE_END" and texts.get(ev["messageId"], "").strip():
                tx.append(thread_id, new_entry("assistant", text=texts.pop(ev["messageId"])))
            elif t == "RUN_ERROR":
                tx.append(thread_id, new_entry("error", text=ev["message"]))
            elif name == "tool_activity":
                tx.append(thread_id, new_entry("tool", name=ev["value"]["name"], input=ev["value"].get("input")))
            elif name == "memory_compacted":
                tx.append(thread_id, new_entry("notice", text="Earlier messages were summarized for the assistant; "
                                                              "the chat history is kept in full."))
            elif name == "on_interrupt":
                entry = tx.append(thread_id, new_entry("card", changes=ev["value"].get("changes", []), status="pending"))
                ev = {**ev, "value": {**ev["value"], "card_id": entry["id"]}}
            yield ev

    def thread(self, thread_id: str) -> dict[str, Any]:
        """What a client needs to restore a conversation: the transcript and the pending card, if any."""
        entries = self.transcripts.list(check_thread_id(thread_id))
        return {"thread_id": thread_id, "transcript": entries, "pending_card": pending_card(entries)}

    async def delete_thread(self, thread_id: str) -> None:
        """Forget a conversation: its transcript and the model's history."""
        self.transcripts.delete(check_thread_id(thread_id))
        if hasattr(self.checkpointer, "adelete_thread"):
            await self.checkpointer.adelete_thread(thread_id)

    async def _run(self, thread_id: str, *, message: str | None, state: dict[str, Any] | None,
                   resume: dict[str, Any] | None, run_id: str | None) -> AsyncIterator[dict]:
        cfg = {"configurable": {"thread_id": thread_id}}
        run_id = run_id or str(uuid.uuid4())
        if resume is not None:
            inp: Any = Command(resume=resume)
        else:
            st = state or {}
            if not self.layout(st.get("jsx_hash", "")):
                raise KeyError("unknown jsx_hash: call register_form first")
            inp = {"user_text": message or "", "config": st["config"], "jsx_hash": st["jsx_hash"],
                   "form_id": st.get("form_id"), "ui": st.get("ui") or {}, "thread_id": thread_id,
                   "attachments": st.get("attachments") or []}
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
        try:
            async for mode, chunk in self.graph.astream(inp, cfg, stream_mode=["custom", "updates"]):
                if mode == "updates":
                    for it in (chunk.get("__interrupt__") or ()) if isinstance(chunk, dict) else ():
                        yield {"type": "CUSTOM", "name": "on_interrupt", "value": it.value}
                    continue
                k = chunk.get("kind")
                if k == "text_start":
                    yield {"type": "TEXT_MESSAGE_START", "messageId": chunk["id"], "role": "assistant"}
                elif k == "text_delta":
                    yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": chunk["id"], "delta": chunk["delta"]}
                elif k == "text_end":
                    yield {"type": "TEXT_MESSAGE_END", "messageId": chunk["id"]}
                elif k == "ui":
                    yield {"type": "CUSTOM", "name": "ui_directive", "value": chunk["directive"]}
                elif k == "tool":
                    yield {"type": "CUSTOM", "name": "tool_activity", "value": chunk}
                elif k == "note":
                    yield {"type": "CUSTOM", "name": "agent_note", "value": chunk["text"]}
                elif k == "memory":
                    yield {"type": "CUSTOM", "name": "memory_compacted", "value": chunk}
                elif k == "context":
                    yield {"type": "CUSTOM", "name": "agent_context", "value": chunk}
                elif k == "error":
                    yield {"type": "RUN_ERROR", "message": chunk["message"]}
        except Exception as e:  # noqa: BLE001 — report instead of breaking the stream
            yield {"type": "RUN_ERROR", "message": f"{type(e).__name__}: {e}"}
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}

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
