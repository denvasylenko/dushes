"""The docs assistant as an AG-UI endpoint for the site's <agui-chat>.

    DOCS_AI_CORPUS=https://dushes-ai.fly.dev/llms-full.txt \
    DOCS_AI_ORIGINS=https://dushes-ai.fly.dev ANTHROPIC_API_KEY=... \
    uv run uvicorn docs_ai.app:app --port 8100

POST /ask/run takes an AG-UI RunAgentInput and streams: RUN_STARTED, a "search_docs" step, a short answer,
cards (CUSTOM docs_card: code quoted from the docs, pages, steps, live gallery cards), follow-up questions
(CUSTOM suggestions), RUN_FINISHED (or RUN_ERROR). See agent.py. It answers only from the docs, stores nothing,
and limits questions per conversation, per address and per site.

Settings (environment):
  DOCS_AI_CORPUS       llms-full.txt URL or path (default: ../site/dist/llms-full.txt)
  DOCS_AI_MODEL        any init_chat_model string with tool calling (default: anthropic:claude-haiku-5-5)
  DOCS_AI_ORIGINS      comma-separated allowed origins (default: http://localhost:4321)
  DOCS_AI_PER_MINUTE   questions per address per minute (default 6); DOCS_AI_PER_DAY (default 60)
  DOCS_AI_PER_THREAD   questions per conversation (default 15); DOCS_AI_SITE_PER_DAY (default 1000)
  DOCS_AI_MAX_CHARS    longest question (default 2000)
  DOCS_AI_REFRESH      seconds between corpus reloads (default 3600)
  DOCS_AI_RECIPES      folder of answer recipes (default: docs_ai/recipes; see recipes.py)
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, AsyncIterator

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from pydantic import ValidationError

from formguide import agui

from .agent import answer
from .corpus import Corpus, load

log = logging.getLogger("formguide.docs_ai")

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
    return init_chat_model(os.environ.get("DOCS_AI_MODEL", "anthropic:claude-haiku-5-5"), max_tokens=2000)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content or "")


class Quota:
    """Questions per conversation and per site per day. In memory: one process."""

    def __init__(self, per_thread: int, site_per_day: int):
        self.per_thread, self.site_per_day = per_thread, site_per_day
        self.threads: dict[str, int] = defaultdict(int)
        self.site: deque[float] = deque()

    def allow(self, thread_id: str, now: float | None = None) -> str | None:
        """None when allowed, else the reason."""
        now = time.time() if now is None else now
        while self.site and self.site[0] < now - 86400:
            self.site.popleft()
        if self.threads[thread_id] >= self.per_thread:
            return "This chat has reached its limit. Start a new chat, or run Dushes yourself: see the quick start."
        if len(self.site) >= self.site_per_day:
            return "The assistant has answered enough questions for today. Try again tomorrow."
        self.threads[thread_id] += 1
        self.site.append(now)
        if len(self.threads) > 50_000:   # forget the oldest conversations
            for k in list(self.threads)[:10_000]:
                del self.threads[k]
        return None


def create_app(*, corpus_source: str | None = None, model: BaseChatModel | None = None,
               origins: list[str] | None = None, per_minute: int | None = None, per_day: int | None = None,
               max_chars: int | None = None, refresh: float | None = None, per_thread: int | None = None,
               site_per_day: int | None = None) -> FastAPI:
    env = os.environ.get
    source = corpus_source or env("DOCS_AI_CORPUS") or str(Path(__file__).resolve().parents[2] / "site/dist/llms-full.txt")
    limiter = Limiter(per_minute or int(env("DOCS_AI_PER_MINUTE", "6")), per_day or int(env("DOCS_AI_PER_DAY", "60")))
    quota = Quota(per_thread or int(env("DOCS_AI_PER_THREAD", "15")), site_per_day or int(env("DOCS_AI_SITE_PER_DAY", "1000")))
    max_len = max_chars or int(env("DOCS_AI_MAX_CHARS", "2000"))
    every = refresh if refresh is not None else float(env("DOCS_AI_REFRESH", "3600"))
    state: dict[str, Any] = {"corpus": None, "model": model, "loaded": 0.0}

    def reload() -> None:
        try:
            c: Corpus = load(source)
            state["corpus"] = c
            state["loaded"] = time.time()
            log.info("docs corpus: %d pages, %d sections from %s", c.pages, c.sections, c.source)
        except Exception as e:  # noqa: BLE001 — keep the previous corpus
            state["loaded"] = time.time()   # try again after `every`, not on every request
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

    app = FastAPI(title="Dushes docs assistant", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=origins or [o.strip() for o in env("DOCS_AI_ORIGINS", "http://localhost:4321").split(",")],
                       allow_methods=["POST", "GET", "OPTIONS"], allow_headers=["Content-Type", "Accept"])

    @app.get("/health")
    def health() -> dict:
        if state["corpus"] is None:
            reload()
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
        if state["corpus"] is None or (every > 0 and time.time() - state["loaded"] > every):
            await asyncio.to_thread(reload)   # mounted in another app (docs_ai.host) the lifespan does not run
        corpus: Corpus | None = state["corpus"]
        if corpus is None:
            raise HTTPException(503, "The docs are still loading. Try again in a moment.")
        if (why := quota.allow(inp.thread_id)) is not None:
            raise HTTPException(429, why)
        if state["model"] is None:
            state["model"] = default_model()
        enc = agui.encoder(request.headers.get("accept"))

        async def events() -> AsyncIterator[str]:
            async for ev in answer(state["model"], corpus, question, history[-7:-1], inp.thread_id, inp.run_id):
                yield agui.encode(ev, enc)

        return StreamingResponse(events(), media_type=enc.get_content_type(),
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
