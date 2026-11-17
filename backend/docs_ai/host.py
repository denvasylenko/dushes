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
    DEMO_CODE_PER_THREAD  messages per conversation for a person who entered an activation code (100)
    DEMO_CODE_PER_DAY     messages a day for such a person, by address and by visitor (400)
    DEMO_RUNS_DAY         runs a day, card answers and hand-offs included (300)
    DEMO_COST_DAY         US dollars a day in total, from each run's real tokens (run_stats) (5)
    DEMO_COST_CHOICES     dollars a day per model choice, "haiku=3,luna=2"; a choice not named has only the total
    DEMO_PRICES_FILE      the price table, by model id (site/src/data/prices.json: the one the docs' costs use)
    DEMO_PRICES           "input,output,cache_read,cache_write" dollars per million tokens for a model the table
                          lacks; with neither, the cost is not counted and the cost caps are off
    DEMO_KEEP_HOURS       the public demo's transcripts and checkpoints are deleted after this many hours (24;
                          the hourly clean-up runs on Fly or when this is set, never on a local run)
    DEMO_LINK             where a refused visitor is sent (the quickstart)
The routes beside the run that cost something (prefill, attachments, transcription, registering a form) are
under the same daily limits. A refused run gets HTTP 429 {"detail", "code": "demo_limit", "reason": visitor|ip|thread|site|runs|cost, "link"}
before any stream starts. The day's numbers (runs, messages, tokens, cost; never message text) are kept in
<data_dir>/demo/<date>.json.
Uploading business documents (/agent/kb) is off; a user may still attach a file to a message.
The landing's own forms (backend/demo/landing/<form_id>.jsx; the pack is <form_id>.pack.json next to it, else the one
in domain_packs/) are registered at start-up. The chat-only recipe's form, deputy_change, has one tool for that form
only, submit_deputy_change: a stand-in that sends nothing ("Demo: nothing was sent"), held by confirm_tools;
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
from langchain_core.tools import tool
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("DEMO_CONFIG", str(ROOT / "backend/demo/formguide.hosted.yaml"))
os.environ.setdefault("DEMO_PATH", "/demo")
os.environ.setdefault("DEMO_DEBUG", "0")
os.environ.setdefault("DOCS_AI_CORPUS", str(ROOT / "site/dist/llms-full.txt"))

from demo.app import app  # noqa: E402  (reads the variables above)

from formguide.skills import Skill  # noqa: E402

from .app import create_app  # noqa: E402

PER_VISITOR_DAY = int(os.environ.get("DEMO_PER_VISITOR_DAY", "10"))
PER_IP_DAY = int(os.environ.get("DEMO_PER_IP_DAY", "60"))
PER_THREAD = int(os.environ.get("DEMO_PER_THREAD", "15"))
PER_DAY = int(os.environ.get("DEMO_PER_DAY", "500"))
# a person who entered an activation code (the experimental features, or the voice mode) is one of ours: the limits
# of the owner's own dev host. The site's totals (messages, runs, dollars a day) stay the same for everyone.
CODE_PER_THREAD = int(os.environ.get("DEMO_CODE_PER_THREAD", "100"))
CODE_PER_DAY = int(os.environ.get("DEMO_CODE_PER_DAY", "400"))
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


def price_table(path: str | Path | None) -> dict[str, dict]:
    """The price file's rows by model id: {id: {input, output, cache_read, cache_write?, over?: {tokens, ...}}},
    dollars per million tokens. Missing or unreadable: an empty table."""
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8")).get("models") if path else None
    except (OSError, ValueError):
        rows = None
    return {str(k): v for k, v in (rows or {}).items() if isinstance(v, dict) and "input" in v and "output" in v}


def cost_choices(raw: str | None) -> dict[str, float]:
    """DEMO_COST_CHOICES "haiku=3,luna=2" -> {choice: dollars a day}."""
    out = {}
    for part in (raw or "").split(","):
        name, _, value = part.partition("=")
        if name.strip() and value.strip():
            out[name.strip()] = float(value)
    return out


PRICES_FILE = Path(os.environ.get("DEMO_PRICES_FILE") or ROOT / "site/src/data/prices.json")
TABLE = price_table(PRICES_FILE)
COST_CHOICES = cost_choices(os.environ.get("DEMO_COST_CHOICES", "haiku=3,luna=2"))
if TABLE:   # one line at start-up: an operator sees which prices the caps are counted with
    log.warning("demo prices: %d models from %s%s", len(TABLE), PRICES_FILE,
                "; DEMO_PRICES for a model the file lacks" if PRICES is not None else "")
elif PRICES is not None:
    log.warning("demo prices: the price file %s was not found; every model is priced by DEMO_PRICES", PRICES_FILE)
else:
    log.warning("demo prices: no price file (%s) and no DEMO_PRICES: the cost is not counted and the caps are off",
                PRICES_FILE)


def counting() -> bool:
    return PRICES is not None or bool(TABLE)

SENTENCES = {
    "thread": f"This demo chat has reached its {PER_THREAD} messages. Start a new chat, or run formguide yourself in three commands.",
    "visitor": "You have used today's demo messages. Try again tomorrow, or run formguide yourself in three commands.",
    "ip": "You have used today's demo messages. Try again tomorrow, or run formguide yourself in three commands.",
    "site": "The demo has answered enough for today. Try again tomorrow, or run formguide yourself in three commands.",
    "runs": "The demo has answered enough for today. Try again tomorrow, or run formguide yourself in three commands.",
    "cost": "The demo has answered enough for today. Try again tomorrow, or run formguide yourself in three commands.",
    "model_cost": "This model's demo budget for today is used up. Start a new chat on the other model.",
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
        self.by_choice: dict[str, float] = defaultdict(float)   # dollars per model choice

    def numbers(self) -> dict:
        return {"date": self.date, "runs": self.runs, "messages": self.messages, "visitors": len(self.visitors),
                "tokens": dict(self.tokens), "cost_usd": round(self.cost, 4),
                "cost_by_choice": {k: round(v, 4) for k, v in self.by_choice.items()}}


_threads: dict[str, int] = defaultdict(int)
_day = Day("")


def today(now: float | None = None) -> Day:
    global _day
    date = time.strftime("%Y-%m-%d", time.gmtime(time.time() if now is None else now))
    if _day.date != date:
        _day = Day(date)
    return _day


def left(choice: str | None, now: float | None = None) -> bool:
    """Whether a model choice still has budget today (its own, when it has one, and the total)."""
    d = today(now)
    if not counting():
        return True
    return d.cost < COST_DAY and not (choice in COST_CHOICES and d.by_choice[choice] >= COST_CHOICES[choice])


_holders: dict[str, set[str]] = {}   # the day -> the addresses a right code (or a valid pass) came from


def code_holder(ip: str, now: float | None = None, mark: bool = False) -> bool:
    """Whether a right activation code, or a valid pass, came from this address today; `mark` records one."""
    date = today(now).date
    if mark:
        for old in [d for d in _holders if d != date]:
            del _holders[old]
        _holders.setdefault(date, set()).add(ip)
    return ip in _holders.get(date, ())


def demo_limit(thread_id: str, ip: str, visitor: str | None = None, *, message: bool = True,
               now: float | None = None, choice: str | None = None, holder: bool = False) -> str | None:
    """None when this run may go ahead (and it is counted), else the reason it may not: visitor, ip, thread,
    site, runs, cost (the day's total) or model_cost (the budget of the run's model choice). Only a new message
    counts toward the message limits; every run counts as a run."""
    d = today(now)
    if d.runs >= RUNS_DAY:
        return "runs"
    if counting() and d.cost >= COST_DAY:
        return "cost"
    if counting() and choice in COST_CHOICES and d.by_choice[choice] >= COST_CHOICES[choice]:
        return "model_cost"
    if message:
        # `holder`: a person who entered an activation code has the wider limits (the site's totals still hold)
        if _threads[thread_id] >= (CODE_PER_THREAD if holder else PER_THREAD):
            return "thread"
        if visitor and d.visitors[visitor] >= (CODE_PER_DAY if holder else PER_VISITOR_DAY):
            return "visitor"
        if d.ips[ip] >= (CODE_PER_DAY if holder else PER_IP_DAY):
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


def call_price(model: str | None, prompt_tokens: int) -> tuple[float, float, float, float] | None:
    """Dollars per token (input, output, cache read, cache write) for one call of a model: its row of the price
    table, the `over` tier when the whole prompt is above the tier's size, else DEMO_PRICES, else None."""
    name = str(model or "").split(":")[-1].split("/")[-1]
    row = TABLE.get(name) or next((v for k, v in TABLE.items() if name.startswith(k)), None)
    if row is None:
        return PRICES
    over = row.get("over")
    if isinstance(over, dict) and prompt_tokens > (over.get("tokens") or 0):
        row = {**row, **{k: v for k, v in over.items() if k != "tokens"}}
    write = row.get("cache_write", row["input"] * 1.25)
    return tuple(x / 1e6 for x in (row["input"], row["output"], row.get("cache_read", row["input"]), write))  # type: ignore[return-value]


def run_cost(summary: dict) -> tuple[float, dict]:
    """One run_stats summary -> (dollars, tokens), each call priced by its own model. langchain's input_tokens
    include the cache reads and writes."""
    t = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    cost = 0.0
    for m in summary.get("models") or []:
        c = {"input": m.get("input_tokens") or 0, "output": m.get("output_tokens") or 0,
             "cache_read": m.get("cache_read_tokens") or 0, "cache_write": m.get("cache_write_tokens") or 0}
        for k, v in c.items():
            t[k] += v
        p = call_price(m.get("model"), c["input"])
        if p is not None:
            plain = max(0, c["input"] - c["cache_read"] - c["cache_write"])
            cost += plain * p[0] + c["output"] * p[1] + c["cache_read"] * p[2] + c["cache_write"] * p[3]
    return cost, t


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
        d.by_choice[str(summary.get("choice") or "")] += cost
        for k, v in tokens.items():
            d.tokens[k] += v
        _save_day(d)


_stats = logging.getLogger("formguide.stats")
_stats.addHandler(_Costs())
if _stats.level == logging.NOTSET or _stats.level > logging.INFO:
    _stats.setLevel(logging.INFO)

# the landing's own forms, registered once at start-up: {form_id: jsx_hash}. A form's pack is <form_id>.pack.json
# next to its JSX (given with the form, so no other host sees it), else the one in domain_packs/.
LANDING_DIR = ROOT / "backend/demo/landing"


def _landing_pack(form_id: str) -> dict | None:
    p = LANDING_DIR / f"{form_id}.pack.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


LANDING = {p.stem: guide.register_form(p.read_text(encoding="utf-8"), p.stem, _landing_pack(p.stem))["jsx_hash"]
           for p in sorted(LANDING_DIR.glob("*.jsx"))}


@tool
def submit_deputy_change(summary: str) -> dict:
    """Send the deputy change once all four values are set. summary: the deputy's name and email, the start date
    and the reason."""
    # the public demo's stand-in for a host's own tool: it sends nothing and stores nothing
    return {"text": "Demo: nothing was sent.", "receipt": {"title": "Demo: nothing was sent"}}


# the chat-only recipe's live tile: the send tool exists for that form only, behind the system's confirmation card
guide.skills.add(Skill(name="send_deputy_change", description="Send the finished deputy change.",
                       instructions="When all four values are set, call submit_deputy_change with a one-line summary.",
                       tools=[submit_deputy_change], forms={"deputy_change"}))
if "submit_deputy_change" not in (guide.config.confirm_tools or []):
    guide.config.confirm_tools = [*(guide.config.confirm_tools or []), "submit_deputy_change"]


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


def refused(reason: str, **more: str) -> JSONResponse:
    return JSONResponse({"detail": SENTENCES[reason], "code": "demo_limit", "reason": reason, "link": LINK, **more},
                        status_code=429)


def choices() -> list[dict]:
    """The model choices of the demo, each with `left`: whether it still has budget today."""
    return [{**c, "left": left(c["name"])} for c in guide.model_choices()]


def other_choice(name: str) -> dict | None:
    """Another choice that can answer now: usable and with budget left."""
    return next((c for c in choices() if c["name"] != name and c["usable"] and c["left"]), None)


def _with_notice(response, notice: dict, accept: str | None):
    """The run's stream with one CUSTOM `notice` event after its first event (RUN_STARTED stays first)."""
    from formguide import agui
    enc = agui.encoder(accept)
    extra = agui.encode({"type": "CUSTOM", "name": "notice", "value": notice}, enc)
    inner = response.body_iterator

    async def body():
        first = True
        async for chunk in inner:
            yield chunk
            if first:
                first = False
                yield extra.encode() if isinstance(extra, str) else extra

    response.body_iterator = body()
    return response


_VISITOR = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
# every other route that costs something on a public host: a model call (prefill, transcription), a stored file
# (attachments) or a registered form (layouts). Each counts per visitor, per address and for the whole site.
METERED = frozenset({"/agent/prefill", "/agent/attachments", "/agent/transcribe", "/site/transcribe", "/agent/layouts"})


def _holds_pass(headers) -> bool:
    """Whether the request carries a valid pass of the experimental features or of the voice mode."""
    try:
        from demo.app import _EXPERIMENTS
        if _EXPERIMENTS.enabled and _EXPERIMENTS.person(headers):
            return True
        voice_talks = globals().get("VOICE")
        return bool(voice_talks is not None and voice_talks.config.enabled and voice_talks.gate.person(headers.get("x-voice-pass")))
    except Exception:  # noqa: BLE001 - a pass that cannot be read is no pass
        return False


@app.middleware("http")
async def public_demo(request, call_next):
    path, method = request.url.path, request.method
    ip = request.headers.get("fly-client-ip") or (request.client.host if request.client else "?")
    if method == "POST" and path in ("/experiments/unlock", "/voice/unlock"):
        response = await call_next(request)
        if response.status_code == 200:          # a right code: this address is a code holder for today
            code_holder(ip, mark=True)
        return response
    if _holds_pass(request.headers):             # a kept pass (after a restart, or on a new day): the same
        code_holder(ip, mark=True)
    if path.startswith("/agent/kb") and method in ("POST", "DELETE"):
        return JSONResponse({"detail": "Uploading documents is off in the public demo."}, status_code=403)
    if method == "GET" and path.startswith("/agent/layouts/") and path.rsplit("/", 1)[1] in LANDING:
        fid = path.rsplit("/", 1)[1]   # a landing form by its id: read-only
        return JSONResponse({"jsx_hash": LANDING[fid], "form_id": fid})
    if method == "POST" and path in METERED:   # they call a model or store a file: the same daily limits as a message
        visitor = request.headers.get("x-demo-visitor") or ""
        why = demo_limit(f"{path}|{ip}|{today().date}", ip, visitor if _VISITOR.match(visitor) else None,
                         message=path != "/agent/layouts",   # registering a form counts as a run, not a message
                         holder=code_holder(ip))
        _save_day(today())
        if why:
            return refused(why)
        return await call_next(request)
    if method == "GET" and path == "/agent/models":   # the demo's model choices, with today's budgets
        return JSONResponse({"choices": choices()})
    if path in ("/agent/run", "/site/run", "/ai/ask/run", "/research/run") and method == "POST":   # every demo that answers
        try:
            body = json.loads(await request.body() or b"{}")
        except ValueError:
            body = {}
        props = body.get("forwardedProps") if isinstance(body.get("forwardedProps"), dict) else {}
        thread = str(body.get("threadId") or "?")
        ask = path == "/ai/ask/run"              # the docs assistant counts its own messages, and may change model
        names = [c["name"] for c in guide.model_choices()]
        # a form or site conversation keeps its model; a docs or researcher question may name another each time
        fixed = None if ask or path == "/research/run" or not names else guide.thread_choice(thread)
        choice = (fixed or props.get("model") or names[0]) if names else None
        notice = None
        if choice in names and not left(choice) and today().cost < COST_DAY:
            other = other_choice(choice)
            if other is None:
                return refused("cost")
            if fixed:                            # an existing conversation cannot change its model
                return refused("model_cost", choice=choice, other=other["name"])
            label = next(c["label"] for c in guide.model_choices() if c["name"] == choice)
            notice = {"text": f"{label}'s demo budget for today is used up; {other['label']} answers.",
                      "code": "model_fallback", "choice": other["name"]}
            choice = other["name"]
            body["forwardedProps"] = {**props, "model": choice}
            request._body = json.dumps(body).encode()   # the run goes on with the other choice
        if ask:
            if counting() and today().cost >= COST_DAY:
                return refused("cost")
        else:
            message = not props.get("command") and not props.get("handoff") and not body.get("resume")
            visitor = request.headers.get("x-demo-visitor") or ""
            why = demo_limit(thread, ip, visitor if _VISITOR.match(visitor) else None, message=message,
                             choice=choice, holder=code_holder(ip))
            _save_day(today())
            if why:
                return refused(why)
        response = await call_next(request)
        if notice and response.status_code == 200:
            response = _with_notice(response, notice, request.headers.get("accept"))
        return response
    return await call_next(request)


from .research_demo import create_router as _research_router  # noqa: E402

app.include_router(_research_router(guide), prefix="/research")   # the researcher demo over the invented corpora
_sets = guide._choices
app.mount("/ai", create_app(refresh=3600,
                            models={n: s.models.agent for n, s in _sets.items() if not s.error} or None,
                            labels={n: s.label for n, s in _sets.items()}))
# the experimental voice mode: only when the host has voice codes (VOICE_CODES); without them none of this exists
from formguide import voice as _voice  # noqa: E402

VOICE = _voice.Talks(_voice.VoiceConfig.from_env(), title="the Dushes demo", log_dir=Path(guide.data_dir) / "voice",
                     stop=guide.stop)   # speaking over an answer stops the turn in progress
if VOICE.config.enabled:
    from fastapi import HTTPException, Request  # noqa: E402
    from fastapi.responses import HTMLResponse  # noqa: E402

    app.include_router(_voice.create_voice_router(_voice.watch(VOICE)), prefix="/voice")
    from demo.app import _EXPERIMENTS  # noqa: E402
    _EXPERIMENTS.join("voice", VOICE.gate)   # one code field in "+" opens what the code is listed for

    _CLIPS = os.environ.get("VOICE_LAB_CLIPS")   # recorded clips for tests without a microphone (the lab's ?clip=)
    if _CLIPS and Path(_CLIPS).is_dir():
        app.mount("/voice-lab/clips", StaticFiles(directory=_CLIPS), name="voice-clips")

    @app.get("/voice/open")
    def voice_open(request: Request) -> dict:
        """How many voice conversations are open: for the local dev host's own script, which must not restart the
        server under one. Answered to this machine only; from anywhere else the route does not exist."""
        if not request.client or request.client.host not in ("127.0.0.1", "::1"):
            raise HTTPException(404)
        return {"open": len(VOICE.meter.open)}

    @app.get("/voice-lab/", response_class=HTMLResponse)
    def voice_lab() -> str:   # the owner's first test page: the demo form with a microphone (not the product's UI)
        return (Path(__file__).parent / "voice_lab.html").read_text(encoding="utf-8")

_SITE = ROOT / "site" / "dist"
if _SITE.exists():
    app.mount("/", StaticFiles(directory=_SITE, html=True), name="docs")
