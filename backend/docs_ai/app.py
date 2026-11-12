"""The docs assistant as an AG-UI endpoint for the site's <agui-chat>.

    DOCS_AI_CORPUS=https://denvasylenko.github.io/dushes/llms-full.txt \
    DOCS_AI_ORIGINS=https://denvasylenko.github.io ANTHROPIC_API_KEY=... \
    uv run uvicorn docs_ai.app:app --port 8100

POST /ask/run takes an AG-UI RunAgentInput and streams: RUN_STARTED, a "search_docs" tool step, the answer,
RUN_FINISHED (or RUN_ERROR). It answers only from the docs, stores nothing, and limits requests per address.

Settings (environment):
  DOCS_AI_CORPUS       llms-full.txt URL or path (default: ../site/dist/llms-full.txt)
  DOCS_AI_MODEL        any init_chat_model string (default: anthropic:claude-sonnet-5-5)
  DOCS_AI_ORIGINS      comma-separated allowed origins (default: http://localhost:4321)
  DOCS_AI_PER_MINUTE   questions per address per minute (default 6); DOCS_AI_PER_DAY (default 60)
  DOCS_AI_MAX_CHARS    longest question (default 2000)
  DOCS_AI_REFRESH      seconds between corpus reloads (default 3600)
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, AsyncIterator

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from formguide import agui

from .corpus import Corpus, load

log = logging.getLogger("formguide.docs_ai")

SYSTEM = """You are the documentation assistant for formguide, a chat agent that guides people through large forms \
(Python backend on LangGraph with any LangChain model, AG-UI on the wire, the <agui-chat> Web Component in the browser).

Answer ONLY from the documentation passages below. Rules:
- Be short and practical: one or two sentences, then the code.
- When the question is about doing something, give a complete snippet the reader can paste (YAML, Python, TypeScript, \
HTML or bash), in a fenced block with the language. Never invent keys, options, endpoints or functions that the \
passages do not show.
- If the passages do not answer the question, say so in one sentence and point to the closest page.
- End with a line "Sources:" and a Markdown link for each passage you used: [section title](address).
- Answer in the language of the question.

Documentation passages:
{passages}"""


class Limiter:
    """Questions per address: a sliding minute and a sliding day. In memory: one process."""

    def __init__(self, per_minute: int, per_day: int):
        self.per_minute, self.per_day = per_minute, per_day
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        q = self.hits[key]
        while q and q[0] < now - 86400:
            q.popleft()
        recent = sum(1 for t in q if t > now - 60)
        if recent >= self.per_minute or len(q) >= self.per_day:
            return False
        q.append(now)
        return True


def default_model() -> BaseChatModel:
    from langchain.chat_models import init_chat_model
    return init_chat_model(os.environ.get("DOCS_AI_MODEL", "anthropic:claude-sonnet-5-5"), max_tokens=2500)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content or "")


def passages(chunks: list) -> str:
    return "\n\n".join(f"<passage title=\"{c.title} / {c.section}\" address=\"{c.doc_id}\">\n{c.text}\n</passage>" for c in chunks)


def create_app(*, corpus_source: str | None = None, model: BaseChatModel | None = None,
               origins: list[str] | None = None, per_minute: int | None = None, per_day: int | None = None,
               max_chars: int | None = None, refresh: float | None = None) -> FastAPI:
    env = os.environ.get
    source = corpus_source or env("DOCS_AI_CORPUS") or str(Path(__file__).resolve().parents[2] / "site/dist/llms-full.txt")
    limiter = Limiter(per_minute or int(env("DOCS_AI_PER_MINUTE", "6")), per_day or int(env("DOCS_AI_PER_DAY", "60")))
    max_len = max_chars or int(env("DOCS_AI_MAX_CHARS", "2000"))
    every = refresh if refresh is not None else float(env("DOCS_AI_REFRESH", "3600"))
    state: dict[str, Any] = {"corpus": None, "model": model}

    def reload() -> None:
        try:
            c: Corpus = load(source)
            state["corpus"] = c
            log.info("docs corpus: %d pages, %d sections from %s", c.pages, c.sections, c.source)
        except Exception as e:  # noqa: BLE001 — keep the previous corpus
            log.warning("docs corpus not reloaded from %s: %s", source, e)

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI):
        await asyncio.to_thread(reload)

        async def loop() -> None:
            while every > 0:
                await asyncio.sleep(every)
                await asyncio.to_thread(reload)

        task = asyncio.create_task(loop())
        yield
        task.cancel()

    app = FastAPI(title="formguide docs assistant", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=origins or [o.strip() for o in env("DOCS_AI_ORIGINS", "http://localhost:4321").split(",")],
                       allow_methods=["POST", "GET", "OPTIONS"], allow_headers=["Content-Type", "Accept"])

    @app.get("/health")
    def health() -> dict:
        c = state["corpus"]
        return {"ok": c is not None, "pages": c.pages if c else 0, "sections": c.sections if c else 0}

    @app.post("/ask/run")
    async def run(request: Request) -> StreamingResponse:
        try:
            inp = RunAgentInput.model_validate(await request.json())
        except (ValidationError, ValueError) as e:
            raise HTTPException(422, f"not an AG-UI RunAgentInput: {e}") from None
        history = [(m.role, _text(getattr(m, "content", ""))) for m in inp.messages if m.role in ("user", "assistant")]
        question = next((t for r, t in reversed(history) if r == "user"), "").strip()
        if not question:
            raise HTTPException(400, "no question")
        if len(question) > max_len:
            raise HTTPException(413, f"the question is longer than {max_len} characters")
        client = request.headers.get("fly-client-ip") or (request.client.host if request.client else "?")
        if not limiter.allow(client):
            raise HTTPException(429, "Too many questions. Try again in a minute.")
        corpus: Corpus | None = state["corpus"]
        if corpus is None:
            raise HTTPException(503, "The docs are still loading. Try again in a moment.")
        if state["model"] is None:
            state["model"] = default_model()
        enc = agui.encoder(request.headers.get("accept"))

        async def events() -> AsyncIterator[str]:
            async for ev in answer(state["model"], corpus, question, history[-7:-1], inp.thread_id, inp.run_id):
                yield agui.encode(ev, enc)

        return StreamingResponse(events(), media_type=enc.get_content_type(),
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


async def answer(model: BaseChatModel, corpus: Corpus, question: str, history: list[tuple[str, str]],
                 thread_id: str, run_id: str) -> AsyncIterator[dict]:
    """One answer as AG-UI events (dicts)."""
    yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
    call = f"call_{uuid.uuid4().hex[:12]}"
    yield {"type": "TOOL_CALL_START", "toolCallId": call, "toolCallName": "search_docs"}
    yield {"type": "TOOL_CALL_ARGS", "toolCallId": call, "delta": json.dumps({"query": question})}
    yield {"type": "TOOL_CALL_END", "toolCallId": call}
    prev = " ".join(t for r, t in history if r == "user")[-400:]
    found = corpus.search(f"{question} {prev}".strip(), k=7)
    yield {"type": "TOOL_CALL_RESULT", "toolCallId": call, "messageId": f"tool_{uuid.uuid4().hex[:12]}",
           "content": "\n".join(f"{c.title} / {c.section}: {c.doc_id}" for c in found) or "nothing found", "role": "tool"}
    msgs = [SystemMessage(SYSTEM.format(passages=passages(found) or "(no passage matched)"))]
    for role, text in history:
        msgs.append(HumanMessage(text) if role == "user" else AIMessage(text))
    msgs.append(HumanMessage(question))
    mid = f"msg_{uuid.uuid4().hex[:12]}"
    started = False
    try:
        async for chunk in model.astream(msgs):
            delta = _text(chunk.content)
            if not delta:
                continue
            if not started:
                yield {"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"}
                started = True
            yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": delta}
    except Exception as e:  # noqa: BLE001 — a human error, never a stack trace
        log.exception("docs answer failed")
        if started:
            yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
        yield {"type": "RUN_ERROR", "message": "The assistant is unavailable right now. Try again." if "key" not in str(e).lower()
               else "The assistant is not configured (no model key)."}
        return
    if started:
        yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
    yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}


app = create_app()
