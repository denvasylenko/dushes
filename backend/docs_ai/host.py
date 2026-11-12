"""One public host for formguide: the docs site, Ask AI and the live demo, in one app (deploy/docs-ai/).

    /            the docs site (site/dist, built with DOCS_BASE=/)
    /ai/...      the docs assistant: /ai/ask/run, /ai/health (docs_ai.app)
    /demo/       the demo page with the loan form (frontend/dist, built with --base /demo/)
    /agent/...   formguide for the demo (demo.app with formguide.hosted.yaml: Claude Haiku)
    /java/...    the demo's mock form backend

The demo is public, so it is limited (environment):
    DEMO_PER_THREAD     messages per conversation (default 15)
    DEMO_PER_IP_DAY     messages per address per day (default 60)
    DEMO_PER_DAY        messages for the whole site per day (default 500)
Uploading business documents (/agent/kb) is off; a user may still attach a file to a message.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("DEMO_CONFIG", str(ROOT / "backend/demo/formguide.hosted.yaml"))
os.environ.setdefault("DEMO_PATH", "/demo")
os.environ.setdefault("DEMO_DEBUG", "0")
os.environ.setdefault("DOCS_AI_CORPUS", str(ROOT / "site/dist/llms-full.txt"))

from demo.app import app  # noqa: E402  (reads the variables above)

from .app import create_app  # noqa: E402

PER_THREAD = int(os.environ.get("DEMO_PER_THREAD", "15"))
PER_IP_DAY = int(os.environ.get("DEMO_PER_IP_DAY", "60"))
PER_DAY = int(os.environ.get("DEMO_PER_DAY", "500"))

_threads: dict[str, int] = defaultdict(int)
_ips: dict[str, deque[float]] = defaultdict(deque)
_site: deque[float] = deque()


def demo_limit(thread_id: str, ip: str, now: float | None = None) -> str | None:
    """None when this message may run, else the sentence the chat shows."""
    now = time.time() if now is None else now
    for q in (_ips[ip], _site):
        while q and q[0] < now - 86400:
            q.popleft()
    if _threads[thread_id] >= PER_THREAD:
        return f"This demo chat has reached its {PER_THREAD} messages. Start a new chat, or run formguide yourself in three commands."
    if len(_ips[ip]) >= PER_IP_DAY:
        return "You have used today's demo messages. Try again tomorrow, or run formguide yourself."
    if len(_site) >= PER_DAY:
        return "The demo has answered enough for today. Try again tomorrow."
    _threads[thread_id] += 1
    _ips[ip].append(now)
    _site.append(now)
    return None


@app.middleware("http")
async def public_demo(request, call_next):
    path, method = request.url.path, request.method
    if path.startswith("/agent/kb") and method in ("POST", "DELETE"):
        return JSONResponse({"detail": "Uploading documents is off in the public demo."}, status_code=403)
    if path == "/agent/run" and method == "POST":
        try:
            body = json.loads(await request.body() or b"{}")
        except ValueError:
            body = {}
        props = body.get("forwardedProps") or {}
        if not props.get("command") and not body.get("resume"):   # a new message, not a card's answer
            ip = request.headers.get("fly-client-ip") or (request.client.host if request.client else "?")
            why = demo_limit(str(body.get("threadId") or "?"), ip)
            if why:
                return JSONResponse({"detail": why}, status_code=429)
    return await call_next(request)


app.mount("/ai", create_app(refresh=3600))
_SITE = ROOT / "site" / "dist"
if _SITE.exists():
    app.mount("/", StaticFiles(directory=_SITE, html=True), name="docs")
