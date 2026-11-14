"""One public host for formguide: the docs site, Ask AI and the live demo, in one app (deploy/docs-ai/).

    /            the docs site (site/dist, built with DOCS_BASE=/)
    /ai/...      the docs assistant: /ai/ask/run, /ai/health (docs_ai.app)
    /demo/       the demo page with the loan form (frontend/dist, built with --base /demo/)
    /agent/...   formguide for the demo (demo.app with formguide.hosted.yaml: Claude Haiku)
    /java/...    the demo's mock form backend
    /site/...    Dushes over a small demo site (/demo/site.html; demo/site_app.py)

The demo is public, so it is limited (environment, defaults in brackets):
    DEMO_PER_VISITOR_DAY  messages per visitor a day, by the X-Demo-Visitor header the landing sends (10)
    DEMO_PER_IP_DAY       messages per address a day (60)
    DEMO_PER_THREAD       messages per conversation (15)
    DEMO_PER_DAY          messages for the whole site a day (500)
    DEMO_RUNS_DAY         runs a day, card answers and hand-offs included (300)
    DEMO_COST_DAY         US dollars a day, from each run's real tokens (run_stats) (5)
    DEMO_PRICES           "input,output,cache_read,cache_write" dollars per million tokens of the hosted model;
                          unset: the cost is not counted and the cost cap is off
    DEMO_KEEP_HOURS       the public demo's transcripts and checkpoints are deleted after this many hours (24;
                          the hourly clean-up runs on Fly or when this is set, never on a local run)
    DEMO_LINK             where a refused visitor is sent (the quickstart)
A refused run gets HTTP 429 {"detail", "code": "demo_limit", "reason": visitor|ip|thread|site|runs|cost, "link"}
before any stream starts. The day's numbers (runs, messages, tokens, cost; never message text) are kept in
<data_dir>/demo/<date>.json.
Uploading business documents (/agent/kb) is off; a user may still attach a file to a message.
The landing's own form (backend/demo/landing/<form_id>.jsx, its pack in domain_packs/) is registered at start-up;
GET /agent/layouts/<form_id> gives its {jsx_hash, form_id}, so the public page calls no write endpoint.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import time
from collections import defaultdict
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

PER_VISITOR_DAY = int(os.environ.get("DEMO_PER_VISITOR_DAY", "10"))
PER_IP_DAY = int(os.environ.get("DEMO_PER_IP_DAY", "60"))
PER_THREAD = int(os.environ.get("DEMO_PER_THREAD", "15"))
PER_DAY = int(os.environ.get("DEMO_PER_DAY", "500"))
RUNS_DAY = int(os.environ.get("DEMO_RUNS_DAY", "300"))
COST_DAY = float(os.environ.get("DEMO_COST_DAY", "5"))
KEEP_HOURS = float(os.environ.get("DEMO_KEEP_HOURS", "24"))
LINK = os.environ.get("DEMO_LINK", "/get-started/quickstart/")
log = logging.getLogger("docs_ai.host")


def prices(raw: str | None) -> tuple[float, float, float, float] | None:
    """DEMO_PRICES "input,output,cache_read[,cache_write]" (dollars per million tokens) -> dollars per token."""
    if not raw:
        return None
    parts = [float(x) for x in raw.split(",")]
    if len(parts) == 3:
        parts.append(parts[0] * 1.25)   # a cache write costs a quarter more than plain input
    if len(parts) != 4:
        raise ValueError("DEMO_PRICES: input,output,cache_read[,cache_write] per million tokens")
    return tuple(x / 1e6 for x in parts)  # type: ignore[return-value]


PRICES = prices(os.environ.get("DEMO_PRICES"))
if PRICES is None:
    log.warning("DEMO_PRICES is not set: the demo's cost is not counted and DEMO_COST_DAY is off")

SENTENCES = {
    "thread": f"This demo chat has reached its {PER_THREAD} messages. Start a new chat, or run formguide yourself in three commands.",
    "visitor": "You have used today's demo messages. Try again tomorrow, or run formguide yourself in three commands.",
    "ip": "You have used today's demo messages. Try again tomorrow, or run formguide yourself in three commands.",
    "site": "The demo has answered enough for today. Try again tomorrow, or run formguide yourself in three commands.",
    "runs": "The demo has answered enough for today. Try again tomorrow, or run formguide yourself in three commands.",
    "cost": "The demo has answered enough for today. Try again tomorrow, or run formguide yourself in three commands.",
}


class Day:
    """Today's counters; a new day starts them again. Numbers and ids only, never message text."""

    def __init__(self, date: str):
        self.date = date
        self.visitors: dict[str, int] = defaultdict(int)
        self.ips: dict[str, int] = defaultdict(int)
        self.messages = 0
        self.runs = 0
        self.tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        self.cost = 0.0

    def numbers(self) -> dict:
        return {"date": self.date, "runs": self.runs, "messages": self.messages, "visitors": len(self.visitors),
                "tokens": dict(self.tokens), "cost_usd": round(self.cost, 4)}


_threads: dict[str, int] = defaultdict(int)
_day = Day("")


def today(now: float | None = None) -> Day:
    global _day
    date = time.strftime("%Y-%m-%d", time.gmtime(time.time() if now is None else now))
    if _day.date != date:
        _day = Day(date)
    return _day


def demo_limit(thread_id: str, ip: str, visitor: str | None = None, *, message: bool = True,
               now: float | None = None) -> str | None:
    """None when this run may go ahead (and it is counted), else the reason it may not: visitor, ip, thread,
    site, runs or cost. Only a new message counts toward the message limits; every run counts as a run."""
    d = today(now)
    if d.runs >= RUNS_DAY:
        return "runs"
    if PRICES is not None and d.cost >= COST_DAY:
        return "cost"
    if message:
        if _threads[thread_id] >= PER_THREAD:
            return "thread"
        if visitor and d.visitors[visitor] >= PER_VISITOR_DAY:
            return "visitor"
        if d.ips[ip] >= PER_IP_DAY:
            return "ip"
        if d.messages >= PER_DAY:
            return "site"
        _threads[thread_id] += 1
        d.ips[ip] += 1
        d.messages += 1
        if visitor:
            d.visitors[visitor] += 1
    d.runs += 1
    return None


def run_cost(summary: dict) -> tuple[float, dict]:
    """One run_stats summary -> (dollars, tokens). langchain's input_tokens include the cache reads and writes."""
    t = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for m in summary.get("models") or []:
        t["input"] += m.get("input_tokens") or 0
        t["output"] += m.get("output_tokens") or 0
        t["cache_read"] += m.get("cache_read_tokens") or 0
        t["cache_write"] += m.get("cache_write_tokens") or 0
    if PRICES is None:
        return 0.0, t
    pin, pout, pread, pwrite = PRICES
    plain = max(0, t["input"] - t["cache_read"] - t["cache_write"])
    return plain * pin + t["output"] * pout + t["cache_read"] * pread + t["cache_write"] * pwrite, t


guide = app.state.guide
COUNTERS = Path(guide.data_dir) / "demo"


def _save_day(d: Day) -> None:
    try:
        COUNTERS.mkdir(parents=True, exist_ok=True)
        (COUNTERS / f"{d.date}.json").write_text(json.dumps(d.numbers()), encoding="utf-8")
    except OSError:
        log.warning("could not write the demo counters", exc_info=True)


class _Costs(logging.Handler):
    """Every finished run's run_stats line (formguide.stats) -> today's tokens and cost."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            summary = json.loads(record.getMessage())
        except (ValueError, TypeError):
            return
        cost, tokens = run_cost(summary)
        d = today()
        d.cost += cost
        for k, v in tokens.items():
            d.tokens[k] += v
        _save_day(d)


_stats = logging.getLogger("formguide.stats")
_stats.addHandler(_Costs())
if _stats.level == logging.NOTSET or _stats.level > logging.INFO:
    _stats.setLevel(logging.INFO)

# the landing's own forms, registered once at start-up: {form_id: jsx_hash}
LANDING_DIR = ROOT / "backend/demo/landing"
LANDING = {p.stem: guide.register_form(p.read_text(encoding="utf-8"), p.stem)["jsx_hash"]
           for p in sorted(LANDING_DIR.glob("*.jsx"))}


async def clean_up(older_than_hours: float = KEEP_HOURS, now: float | None = None) -> int:
    """Delete the public demo's conversations (transcript and checkpoint) last touched over the given hours ago."""
    root = getattr(guide.transcripts, "root", None)
    if root is None or not Path(root).is_dir():
        return 0
    cut = (time.time() if now is None else now) - older_than_hours * 3600
    gone = 0
    for p in Path(root).glob("*.jsonl"):
        try:
            if p.stat().st_mtime < cut:
                await guide.delete_thread(p.stem)
                gone += 1
        except (OSError, ValueError):
            log.warning("could not delete demo thread %s", p.stem, exc_info=True)
    return gone


async def _clean_up_hourly() -> None:
    while True:
        with contextlib.suppress(Exception):
            n = await clean_up()
            if n:
                log.info("deleted %d demo conversations older than %s hours", n, KEEP_HOURS)
        await asyncio.sleep(3600)


@app.on_event("startup")
async def _start_clean_up() -> None:
    # on the public host only (Fly, or DEMO_KEEP_HOURS set): a local run keeps its own conversations
    if os.environ.get("FLY_APP_NAME") or os.environ.get("DEMO_KEEP_HOURS"):
        app.state.demo_clean_up = asyncio.create_task(_clean_up_hourly())


def refused(reason: str) -> JSONResponse:
    return JSONResponse({"detail": SENTENCES[reason], "code": "demo_limit", "reason": reason, "link": LINK},
                        status_code=429)


_VISITOR = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@app.middleware("http")
async def public_demo(request, call_next):
    path, method = request.url.path, request.method
    if path.startswith("/agent/kb") and method in ("POST", "DELETE"):
        return JSONResponse({"detail": "Uploading documents is off in the public demo."}, status_code=403)
    if method == "GET" and path.startswith("/agent/layouts/") and path.rsplit("/", 1)[1] in LANDING:
        fid = path.rsplit("/", 1)[1]   # a landing form by its id: read-only
        return JSONResponse({"jsx_hash": LANDING[fid], "form_id": fid})
    if path in ("/agent/run", "/site/run") and method == "POST":   # the form demo and the site demo
        try:
            body = json.loads(await request.body() or b"{}")
        except ValueError:
            body = {}
        props = body.get("forwardedProps") or {}
        message = not props.get("command") and not props.get("handoff") and not body.get("resume")
        ip = request.headers.get("fly-client-ip") or (request.client.host if request.client else "?")
        visitor = request.headers.get("x-demo-visitor") or ""
        why = demo_limit(str(body.get("threadId") or "?"), ip, visitor if _VISITOR.match(visitor) else None,
                         message=message)
        _save_day(today())
        if why:
            return refused(why)
    return await call_next(request)


app.mount("/ai", create_app(refresh=3600))
_SITE = ROOT / "site" / "dist"
if _SITE.exists():
    app.mount("/", StaticFiles(directory=_SITE, html=True), name="docs")
