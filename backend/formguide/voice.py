"""Experimental voice mode: who may use it, and how much (openspec/changes/voice-mode).

A voice model listens and speaks; the agent does the work as in chat. This module is the part every host shares:

    VoiceConfig      the codes (one per person), the limits, the price of a minute
    Gate             a code -> a signed pass; the pass -> the person; wrong tries are limited per address
    Meter            the day's voice budget and the limits of one conversation, counted from the seconds the
                     voice provider reports

Nothing here talks to a network. The session with the voice provider and the bridge to a run are in the next
slice (tasks 2.2 to 2.6); they use Gate and Meter as they stand.

A host builds a VoiceConfig (VoiceConfig.from_env reads VOICE_CODES and the VOICE_* limits) and mounts the routes.
With no code set there is no voice mode: `enabled` is false and a host mounts nothing.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

try:   # the routes need the HTTP layer; Gate, Meter and Talks do not
    from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import StreamingResponse
except ImportError:  # pragma: no cover
    APIRouter = HTTPException = Request = StreamingResponse = WebSocket = WebSocketDisconnect = None  # type: ignore[assignment,misc]

_NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _cyr(*codes: int) -> str:
    """A Cyrillic word from its code points: this file stays ASCII (the repository is English-only)."""
    return "".join(map(chr, codes))

PASS_HOURS = 12.0          # how long a pass lives
TRIES_PER_DAY = 5          # wrong codes per address a day, then every try is refused
MIN_CODE_CHARS = 8


@dataclass
class VoiceConfig:
    codes: dict[str, str] = field(default_factory=dict)   # person -> their code
    model: str = "gpt-live-1"
    minute_usd: float = 0.05        # the voice provider's price of a connected minute, silence included
    day_usd: float = 5.0            # this host's voice budget for a day
    person_day_usd: float = 0.0     # a person's own daily budget inside it (0: none)
    max_seconds: int = 300          # one conversation ends here
    max_usd: float = 0.75           # or here, whichever comes first (the voice and the agent's turns together)
    at_once: int = 1                # voice conversations at the same time, on this host
    at_once_person: int = 1         # and for one person
    silence_seconds: int = 30       # this long without speech ends a conversation
    secret: str = ""                # signs the passes; empty: a new one at every start (passes die with the process)

    @property
    def enabled(self) -> bool:
        return bool(self.codes)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> VoiceConfig:
        """VOICE_CODES="anna=<code>,ben=<code>" and optional VOICE_DAY_USD, VOICE_PERSON_DAY_USD, VOICE_MAX_SECONDS,
        VOICE_MAX_USD, VOICE_AT_ONCE, VOICE_SILENCE_SECONDS, VOICE_MODEL, VOICE_MINUTE_USD, VOICE_SECRET."""
        env = os.environ if env is None else env
        cfg = cls(codes=parse_codes(env.get("VOICE_CODES", "")))
        for key, attr, cast in (("VOICE_DAY_USD", "day_usd", float), ("VOICE_PERSON_DAY_USD", "person_day_usd", float),
                                ("VOICE_MAX_SECONDS", "max_seconds", int), ("VOICE_MAX_USD", "max_usd", float),
                                ("VOICE_AT_ONCE", "at_once", int), ("VOICE_SILENCE_SECONDS", "silence_seconds", int),
                                ("VOICE_MODEL", "model", str), ("VOICE_MINUTE_USD", "minute_usd", float),
                                ("VOICE_SECRET", "secret", str)):
            if env.get(key):
                setattr(cfg, attr, cast(env[key]))
        return cfg


def parse_codes(raw: str) -> dict[str, str]:
    """"anna=<code>,ben=<code>" -> {person: code}. A pair that is malformed, a name that is not a plain word, a
    code shorter than eight characters and a code two people share are all errors: a host must not start with a
    weak or ambiguous list."""
    out: dict[str, str] = {}
    for pair in (p.strip() for p in (raw or "").split(",")):
        if not pair:
            continue
        name, sep, code = pair.partition("=")
        name, code = name.strip(), code.strip()
        if not sep or not _NAME.match(name):
            raise ValueError("VOICE_CODES: each entry is name=code, the name letters, digits, - or _")
        if len(code) < MIN_CODE_CHARS:
            raise ValueError(f"VOICE_CODES: the code of {name} is shorter than {MIN_CODE_CHARS} characters")
        if name in out or code in out.values():
            raise ValueError("VOICE_CODES: a name or a code is there twice")
        out[name] = code
    return out


class Gate:
    """Codes and passes. A code is compared with every person's in constant time; a pass is `name.expiry.signature`,
    signed with the host's secret, so the server keeps no list of them."""

    def __init__(self, config: VoiceConfig, now: Callable[[], float] = time.time):
        self.config = config
        self.now = now
        self._secret = (config.secret or secrets.token_hex(32)).encode()
        self._tries: dict[tuple[str, str], int] = {}   # (day, address) -> wrong tries
        self._hosted: set[str] = set()                 # people the host named itself (see issue)

    def _day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self.now()))

    def _sign(self, body: str) -> str:
        return hmac.new(self._secret, body.encode(), hashlib.sha256).hexdigest()[:32]

    def unlock(self, code: str, address: str = "?") -> tuple[str, str] | None:
        """(person, pass) for a right code; None for a wrong one or for an address that has used up its tries."""
        key = (self._day(), address)
        if self._tries.get(key, 0) >= TRIES_PER_DAY:
            return None
        given = (code or "").strip().encode()
        who = None
        for name, right in self.config.codes.items():   # every code is compared: the time tells nothing
            if hmac.compare_digest(given, right.encode()):
                who = name
        if who is None:
            for old in [k for k in self._tries if k[0] != key[0]]:
                del self._tries[old]
            self._tries[key] = self._tries.get(key, 0) + 1
            return None
        body = f"{who}.{int(self.now() + PASS_HOURS * 3600)}"
        return who, f"{body}.{self._sign(body)}"

    def issue(self, person: str) -> str:
        """A pass for a person the host has already identified its own way (its session, its token): no code is
        asked. The name is the host's (a client id); it must be a plain word."""
        if not _NAME.match(person or ""):
            raise ValueError("a person's name is letters, digits, - or _, at most 40")
        self._hosted.add(person)
        body = f"{person}.{int(self.now() + PASS_HOURS * 3600)}"
        return f"{body}.{self._sign(body)}"

    def person(self, token: str | None) -> str | None:
        """Whose pass this is, or None: malformed, signed by another secret, expired, or its code was withdrawn."""
        parts = (token or "").split(".")
        if len(parts) != 3:
            return None
        name, expiry, signature = parts
        if not hmac.compare_digest(signature, self._sign(f"{name}.{expiry}")):
            return None
        if not expiry.isdigit() or int(expiry) < self.now():
            return None
        if name not in self.config.codes and name not in self._hosted:
            return None
        return name


@dataclass
class Talk:
    """One voice conversation in progress."""
    id: str
    person: str
    started: float
    seconds: float = 0.0        # connected time, as the voice provider last reported it
    agent_usd: float = 0.0      # what the agent's own turns in it cost
    heard: float = 0.0          # when speech was last heard


class Meter:
    """The money and time of voice. The day's spend is the closed conversations plus the open ones; an open one is
    counted from the provider's latest report, or from the clock when the report is late (never less)."""

    def __init__(self, config: VoiceConfig, now: Callable[[], float] = time.time,
                 spent_today: Callable[[str | None], float] | None = None,
                 on_cost: Callable[[str, float, float], None] | None = None):
        # a host with its own ledger keeps the day's spend there: `spent_today(person or None)` gives the dollars
        # of closed conversations today (one person's, or everyone's), and `on_cost(person, usd, seconds)` is
        # told what each conversation cost when it ends. Then the limits survive a restart and show in its reports.
        self.spent_today = spent_today
        self.on_cost = on_cost
        self.config = config
        self.now = now
        self._day = ""
        self._spent: dict[str, float] = {}     # person -> dollars today, closed conversations
        self.open: dict[str, Talk] = {}

    def _roll(self) -> None:
        day = time.strftime("%Y-%m-%d", time.gmtime(self.now()))
        if day != self._day:
            self._day, self._spent = day, {}

    def cost(self, talk: Talk) -> float:
        seconds = max(talk.seconds, self.now() - talk.started)
        return seconds / 60 * self.config.minute_usd + talk.agent_usd

    def spent(self, person: str | None = None) -> float:
        """Dollars today: everyone's, or one person's."""
        self._roll()
        if self.spent_today is not None:
            closed = float(self.spent_today(person) or 0.0)
        else:
            closed = self._spent.get(person, 0.0) if person else sum(self._spent.values())
        return closed + sum(self.cost(t) for t in self.open.values() if not person or t.person == person)

    def refusal(self, person: str) -> str | None:
        """Why a new conversation may not start now: `busy`, `day` or `person_day`; None when it may."""
        if len(self.open) >= self.config.at_once:
            return "busy"
        if sum(t.person == person for t in self.open.values()) >= self.config.at_once_person:
            return "busy"
        if self.spent() >= self.config.day_usd:
            return "day"
        if self.config.person_day_usd and self.spent(person) >= self.config.person_day_usd:
            return "person_day"
        return None

    def start(self, talk_id: str, person: str) -> Talk:
        self._roll()
        talk = Talk(talk_id, person, self.now(), heard=self.now())
        self.open[talk_id] = talk
        return talk

    def report(self, talk_id: str, seconds: float | None = None, agent_usd: float = 0.0, heard: bool = False) -> None:
        """What arrived for a conversation: the provider's seconds so far (a snapshot, not an addition), the cost of
        an agent turn, speech heard."""
        talk = self.open.get(talk_id)
        if not talk:
            return
        if seconds is not None:
            talk.seconds = max(talk.seconds, float(seconds))
        talk.agent_usd += agent_usd
        if heard:
            talk.heard = self.now()

    def over(self, talk_id: str) -> str | None:
        """Why an open conversation must end now: `time`, `money`, `silence` or `day`; None while it may go on."""
        talk = self.open.get(talk_id)
        if not talk:
            return None
        if max(talk.seconds, self.now() - talk.started) >= self.config.max_seconds:
            return "time"
        if self.cost(talk) >= self.config.max_usd:
            return "money"
        if self.now() - talk.heard >= self.config.silence_seconds:
            return "silence"
        if self.spent() >= self.config.day_usd:
            return "day"
        return None

    def end(self, talk_id: str, seconds: float | None = None) -> float:
        """Close a conversation (with the provider's final seconds, when it gave them) and return what it cost."""
        self._roll()
        talk = self.open.pop(talk_id, None)
        if not talk:
            return 0.0
        if seconds is not None:
            talk.seconds = max(talk.seconds, float(seconds))
        else:   # no final figure from the provider: its last report can lag, so never less than the clock
            talk.seconds = max(talk.seconds, self.now() - talk.started)
        cost = talk.seconds / 60 * self.config.minute_usd + talk.agent_usd
        self._spent[talk.person] = self._spent.get(talk.person, 0.0) + cost
        if self.on_cost is not None:
            try:
                self.on_cost(talk.person, cost, talk.seconds)
            except Exception:  # noqa: BLE001 - the host's ledger failing must not break the end of a conversation
                pass
        return cost


# ---------------------------------------------------------------- the conversation: the voice session and the bridge
#
#   browser  <== audio (WebRTC) ==>  the voice provider  <== events (WebSocket, our key) ==>  Talks (this module)
#   browser  <-- GET /voice/events (what was heard, what is spoken, the end) --------------  Talks
#   browser  --> the ordinary run with what was heard, as if typed (POST <agent>/run) ------>  the agent
#   the run's events, watched here by thread id --> the answer's text --> the voice says it
#
# So the agent, its rules, its cards and its transcript are the chat's own; the voice only hears and speaks.

LIVE_HTTP = "https://api.openai.com/v1/live/sessions"
LIVE_WS = "wss://api.openai.com/v1/live/sessions/{id}/attach"
SAY_CHARS = 1200   # an appended result holds at most 500 tokens: the text is cut well under it

INSTRUCTIONS = (
    "You are the voice of the assistant of {title}. Speak the language the person speaks, in short sentences. "
    "You know nothing about this business and can do nothing yourself: every request, question or piece of "
    "information the person gives goes to the backend, and you say its result briefly. Never invent a fact, a "
    "price or a confirmation. Do not greet twice and do not repeat what was already said.")

_MARKUP = re.compile(r"[*_`#>|]+|\[(.*?)\]\((.*?)\)")


EARLY_AHEAD = 20   # a sentence is said early once this much of the next one is written (a lead before a step is not)
_SENTENCE = re.compile(r"[.!?\u2026][\"')\]*_]*\s+")


def ready(text: str, start: int = 0) -> int:
    """How far an answer that is still being written can be said: the end of its last whole sentence that already
    has EARLY_AHEAD characters after it; `start` when there is none yet."""
    ends = [m.end() for m in _SENTENCE.finditer(text, start) if len(text) - m.end() >= EARLY_AHEAD]
    return ends[-1] if ends else start


def _sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?\u2026])\s+", text) if x.strip()]


def spoken(text: str) -> str:
    """An answer's text as words to say: no markup, one paragraph, cut to what one result may hold."""
    plain = _MARKUP.sub(lambda m: m.group(1) or "", text or "")
    return re.sub(r"\s+", " ", plain).strip()[:SAY_CHARS]


async def open_live(key: str, model: str, sdp: str, instructions: str):
    """Create the provider's session for a browser's WebRTC offer and attach to it: (session id, the SDP answer,
    the attached WebSocket). The browser gets the answer only: no key leaves the server."""
    import httpx
    import websockets
    head = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=20) as http:
        r = await http.post(LIVE_HTTP, headers=head, json={
            "session": {"model": model, "instructions": instructions,
                        "delegation": {"type": "client", "acknowledgement_delay_ms": 800}},
            "transport": {"type": "webrtc", "sdp": sdp}})
    if r.status_code >= 300:
        raise RuntimeError(f"the voice provider refused the session ({r.status_code})")
    body = r.json()
    sid = body["session"]["id"]
    ws = await websockets.connect(LIVE_WS.format(id=sid), additional_headers=head, max_size=None)
    return sid, body["transport"]["sdp"], ws


# provider events that come many times a second: their content is recorded as our own events, or not at all
_STREAMED = {"session.input_transcript.delta", "session.output_transcript.delta", "session.output_audio.delta",
             "session.usage.updated"}
STREAM_RATE = 24000   # PCM16 mono, both ways, for a conversation whose audio passes through this server
CONTRACT = 1          # the voice routes and events as CONTRACT.md describes them; a breaking change gets a new number


async def open_live_stream(key: str, model: str, instructions: str):
    """Open the provider's session over its WebSocket transport, for audio that passes through this server:
    (session id, the WebSocket). The audio goes in and comes out on the same socket as the events."""
    import asyncio
    import json

    import websockets
    ws = await websockets.connect(LIVE_HTTP.replace("https://", "wss://"),
                                  additional_headers={"Authorization": f"Bearer {key}"}, max_size=None)
    await ws.send(_json({"type": "session.start", "event_id": "start", "session": {
        "model": model, "instructions": instructions,
        "audio": {"format": {"type": "audio/pcm", "rate": STREAM_RATE}},
        "delegation": {"type": "client", "acknowledgement_delay_ms": 800}}}))
    while True:
        ev = json.loads(await asyncio.wait_for(ws.recv(), 15))
        if ev.get("type") == "session.started":
            return (ev.get("session") or {}).get("id") or f"live_{secrets.token_hex(8)}", ws
        if ev.get("type") == "error":
            await ws.close()
            raise RuntimeError(f"the voice provider refused the session ({(ev.get('error') or {}).get('code')})")


class Talks:
    """The voice conversations of one host: who may start one, what each hears and says, when each ends."""

    def __init__(self, config: VoiceConfig, *, title: str = "this site", key: Callable[[], str] | None = None,
                 opener: Callable | None = None, now: Callable[[], float] = time.time,
                 log_dir: str | os.PathLike | None = None,
                 stop: Callable[[str], Any] | None = None,
                 person_of: Callable[[Any], str | None] | None = None,
                 spent_today: Callable[[str | None], float] | None = None,
                 on_cost: Callable[[str, float, float], None] | None = None):
        # person_of(headers): the host names the person of a request its own way (its session, a bearer token);
        # then no code and no pass are asked on any route. Without it, the pass from /unlock (or gate.issue) is.
        self.person_of = person_of
        # stop(thread_id): ends the agent's turn in progress for that thread (FormGuide.stop). With it, speaking
        # over an answer cancels the turn; without it the turn runs on and only its answer is not spoken.
        self._stop = stop
        # a conversation is recorded when log_dir is given: one JSON line an event (what was heard, what the voice
        # said, the answers handed to it, the clock, the end and its cost), in <log_dir>/<day>_<talk>.jsonl
        self.log_dir = log_dir
        self.config = config
        self.gate = Gate(config, now)
        self.meter = Meter(config, now, spent_today, on_cost)
        self.title = title
        self._key = key or (lambda: os.environ.get("OPENAI_API_KEY", ""))
        self._opener = opener or open_live     # tests give a scripted one
        self._stream_opener = open_live_stream
        self.now = now
        self._live: dict[str, dict] = {}       # talk id -> its state
        self._by_thread: dict[str, str] = {}   # the chat thread -> the talk that speaks its answers

    def who(self, headers: Any) -> str | None:
        """The person of a request: named by the host's own hook, or by the pass in X-Voice-Pass."""
        if self.person_of is not None:
            try:
                named = self.person_of(headers)
            except Exception:  # noqa: BLE001 - a host hook that fails names nobody
                named = None
            return named if named and _NAME.match(named) else None
        return self.gate.person(headers.get("x-voice-pass"))

    # -- starting and ending
    async def start(self, person: str, sdp: str, thread_id: str) -> dict:
        """A new conversation for a person's WebRTC offer: {talk, sdp, limits}. Raises Refused with the reason."""
        why = self.meter.refusal(person)
        if why:
            raise Refused(why)
        import asyncio
        sid, answer, ws = await self._opener(self._key(), self.config.model, sdp, INSTRUCTIONS.format(title=self.title))
        talk = self.meter.start(sid, person)
        state = {"id": sid, "person": person, "ws": ws, "thread": thread_id, "events": asyncio.Queue(), "heard": "", "pending": None,
                 "answer": [], "t0": time.monotonic(), "ended": None}
        self._live[sid] = state
        self._by_thread[thread_id] = sid
        self._record(state, {"type": "started", "model": self.config.model, "t_ms": 0})
        state["reader"] = asyncio.create_task(self._read(sid))
        state["watch"] = asyncio.create_task(self._watch(sid))
        return {"talk": talk.id, "sdp": answer, "contract": CONTRACT,
                "limits": {"seconds": self.config.max_seconds, "silence_seconds": self.config.silence_seconds}}

    async def start_stream(self, person: str, thread_id: str) -> dict:
        """A new conversation whose audio passes through this server (a native app, a test runner: a client that
        must not hold the provider's key and has no WebRTC): {talk, limits}. Feed the microphone with `feed`,
        read the voice's audio from `audio`, the events from `events`. Raises Refused with the reason."""
        why = self.meter.refusal(person)
        if why:
            raise Refused(why)
        import asyncio
        sid, ws = await self._stream_opener(self._key(), self.config.model, INSTRUCTIONS.format(title=self.title))
        talk = self.meter.start(sid, person)
        state = {"id": sid, "person": person, "ws": ws, "thread": thread_id, "events": asyncio.Queue(), "heard": "",
                 "pending": None, "answer": [], "t0": time.monotonic(), "ended": None, "audio": asyncio.Queue(maxsize=600)}
        self._live[sid] = state
        self._by_thread[thread_id] = sid
        self._record(state, {"type": "started", "model": self.config.model, "transport": "stream", "t_ms": 0})
        state["reader"] = asyncio.create_task(self._read(sid))
        state["watch"] = asyncio.create_task(self._watch(sid))
        return {"talk": talk.id, "contract": CONTRACT,
                "limits": {"seconds": self.config.max_seconds, "silence_seconds": self.config.silence_seconds},
                "audio": {"format": "pcm16", "rate": STREAM_RATE, "channels": 1}}

    async def feed(self, talk_id: str, pcm: bytes) -> None:
        """Microphone audio for a stream conversation: raw PCM16 mono at STREAM_RATE, in real time."""
        state = self._live.get(talk_id)
        if not state or not pcm:
            return
        import base64
        try:
            await state["ws"].send(_json({"type": "session.input_audio.append",
                                          "audio": base64.b64encode(pcm[:len(pcm) - len(pcm) % 2]).decode()}))
        except Exception:  # noqa: BLE001
            await self.end(talk_id, "lost")

    async def audio(self, talk_id: str):
        """The voice's audio for a stream conversation, as it comes: raw PCM16 mono at STREAM_RATE."""
        state = self._live.get(talk_id)
        if not state or state.get("audio") is None:
            return
        while True:
            piece = await state["audio"].get()
            if piece is None:
                return
            yield piece

    async def end(self, talk_id: str, reason: str = "closed", seconds: float | None = None) -> float:
        """End a conversation and return what it cost (0 when it was not open)."""
        state = self._live.pop(talk_id, None)
        if not state:
            return 0.0
        self._by_thread.pop(state["thread"], None)
        state["ended"] = reason
        cost = self.meter.end(talk_id, seconds)
        try:
            await state["ws"].send(_json({"type": "session.close"}))
            await state["ws"].close()
        except Exception:  # noqa: BLE001 - the session may be gone already
            pass
        import asyncio
        for name in ("reader", "watch"):
            task = state.get(name)
            if task and task is not asyncio.current_task():
                task.cancel()
        if state.get("audio") is not None:
            try:
                state["audio"].put_nowait(None)
            except Exception:  # noqa: BLE001 - full: the reader ends with the socket
                pass
        self._emit(state, {"type": "ended", "reason": reason, "cost_usd": round(cost, 4),
                           "seconds": round(seconds if seconds is not None else time.monotonic() - state["t0"], 1)})
        state["events"].put_nowait(None)
        return cost

    # -- the provider's events
    def _emit(self, state: dict, ev: dict) -> None:
        ev = {**ev, "t_ms": round((time.monotonic() - state["t0"]) * 1000)}
        state["events"].put_nowait(ev)
        self._record(state, ev)

    def _record(self, state: dict, ev: dict) -> None:
        """One line of the conversation's record. Writing it never breaks a conversation."""
        if not self.log_dir:
            return
        try:
            from pathlib import Path
            folder = Path(self.log_dir)
            folder.mkdir(parents=True, exist_ok=True)
            day = time.strftime("%Y-%m-%d", time.gmtime(self.now()))
            line = {"at": time.strftime("%H:%M:%S", time.gmtime(self.now())), "person": state.get("person"),
                    "thread": state["thread"], **ev}
            with open(folder / f"{day}_{state['id']}.jsonl", "a", encoding="utf-8") as f:
                f.write(_json(line) + "\n")
        except OSError:
            pass

    async def _read(self, talk_id: str) -> None:
        import json
        state = self._live[talk_id]
        try:
            async for raw in state["ws"]:
                ev = json.loads(raw)
                t = ev.get("type")
                if t not in _STREAMED:
                    # the provider's own events, by name, in the record (not sent to the client): what it did when
                    # a short line was not heard or a cut-in changed nothing is read here, not guessed
                    self._record(state, {"type": "live", "event": t, "t_ms": round((time.monotonic() - state["t0"]) * 1000),
                                         **({"code": (ev.get("error") or {}).get("code")} if t == "error" else {})})
                if t == "session.input_transcript.delta":
                    state["heard"] += ev.get("delta", "")
                    self.meter.report(talk_id, heard=True)
                    self._emit(state, {"type": "hearing", "delta": ev.get("delta", "")})   # their words, as they speak
                elif t == "session.delegation.created":   # the voice wants the agent: hand over what was said
                    text, state["heard"] = state["heard"].strip(), ""
                    asked = (ev.get("delegation") or {}).get("id")
                    if text and is_echo(text, state.get("said", [])):
                        # the voice's own words came back through the microphone: not a request from the person
                        self._emit(state, {"type": "echo", "text": text})
                        try:   # an empty note cancels the "let me check" the voice was about to say
                            await state["ws"].send(_json({"type": "session.thinking.append", "event_id": "echo",
                                                          "delegation_id": asked, "content": ""}))
                        except Exception:  # noqa: BLE001
                            pass
                        continue
                    if text and state.get("running"):
                        # the person spoke over a turn in progress: that turn is stopped and its answer is not
                        # spoken; what they said now is the request
                        state["running"], state["skip_run"], state["waiting"] = False, True, None
                        if self._stop is not None:
                            try:
                                self._stop(state["thread"])
                            except Exception:  # noqa: BLE001 - a turn that cannot be stopped still loses its voice
                                pass
                        self._emit(state, {"type": "interrupted"})
                    state["pending"] = asked
                    state["answer"], state["told"], state["spoke"] = [], {}, []
                    if text:
                        # a plain yes or no while a card waits is the answer to that card: the client accepts or
                        # rejects it instead of sending the words as a new message (which would close the card)
                        card, said_yes = state.get("waiting"), yes_or_no(text)
                        answers = ({"answers": {"card_id": card.get("card_id"), "type": card.get("type") or "set_fields",
                                                "accepted": said_yes}} if card and said_yes is not None else {})
                        self._emit(state, {"type": "heard", "text": text, **answers})
                elif t == "session.output_transcript.delta":
                    self.meter.report(talk_id, heard=True)   # the conversation is alive while the voice speaks
                    said = state.setdefault("said", [])
                    said.append((time.monotonic(), ev.get("delta", "")))
                    del said[:-400]
                    self._emit(state, {"type": "spoken", "delta": ev.get("delta", "")})
                elif t == "session.output_audio.delta" and state.get("audio") is not None:
                    import base64
                    try:   # a client that reads too slowly loses sound, never the conversation
                        state["audio"].put_nowait(base64.b64decode(ev.get("delta", "")))
                    except Exception:  # noqa: BLE001
                        pass
                elif t == "session.usage.updated":
                    self.meter.report(talk_id, seconds=(ev.get("usage") or {}).get("seconds"))
                elif t == "session.closed":
                    await self.end(talk_id, ev.get("reason") or "closed", (ev.get("usage") or {}).get("seconds"))
                    return
                elif t == "error":
                    self._emit(state, {"type": "error", "code": (ev.get("error") or {}).get("code")})
        except Exception:  # noqa: BLE001 - a dropped connection ends the conversation, it does not break the host
            pass
        await self.end(talk_id, "lost")

    async def _watch(self, talk_id: str) -> None:
        import asyncio
        while talk_id in self._live:
            if self._live[talk_id].get("waiting"):   # a card waits for an answer: thinking it over is not silence
                self.meter.report(talk_id, heard=True)
            why = self.meter.over(talk_id)
            if why:
                await self.end(talk_id, why)
                return
            await asyncio.sleep(1)

    # -- the agent's run, seen from the HTTP layer
    def seen(self, thread_id: str, ev: dict) -> None:
        """One event of a run of this thread (called for every run: a dictionary lookup when no one is talking).
        The answer's text is collected, and when the run ends the voice gets it to say."""
        talk_id = self._by_thread.get(thread_id)
        state = self._live.get(talk_id) if talk_id else None
        if not state:
            return
        t = ev.get("type")
        if t == "RUN_STARTED":
            state["running"], state["skip_run"] = True, False
        elif state.get("skip_run"):
            return   # the rest of a turn the person spoke over: nothing of it is said
        if t in ("RUN_FINISHED", "RUN_ERROR"):
            state["running"] = False
        if t == "RUN_STARTED":
            state["told"], state["spoke"] = {}, []
        if t == "TEXT_MESSAGE_CONTENT":
            mid = ev.get("messageId")
            state["answer"].append((mid, ev.get("delta", "")))
            # the first sentences go to the voice while the rest is still being written
            told = state.setdefault("told", {})   # message id -> how much of it the voice already has
            text = "".join(d for m, d in state["answer"] if m == mid)
            cut = ready(text, told.get(mid, 0))
            if cut > told.get(mid, 0):
                spoke = state.setdefault("spoke", [])
                new = [x for x in _sentences(spoken(text[told.get(mid, 0):cut])) if x not in spoke]
                piece, told[mid] = " ".join(new), cut
                if piece:
                    spoke.extend(new)
                    self._later(self._say(talk_id, piece, more=True))
        elif t == "CUSTOM" and ev.get("name") == "text_retract":
            gone = (ev.get("value") or {}).get("messageId")
            state["answer"] = [(m, d) for m, d in state["answer"] if m != gone]
            state.setdefault("told", {}).pop(gone, None)
        elif t == "CUSTOM" and ev.get("name") == "run_stats":
            self.meter.report(talk_id, agent_usd=float((ev.get("value") or {}).get("cost_usd") or 0))
        elif t in ("RUN_FINISHED", "RUN_ERROR"):
            text = spoken("".join(d for _, d in state["answer"]))
            for card in ((ev.get("outcome") or {}).get("interrupts") or []):   # structured mode: the card comes here
                if (card.get("metadata") or {}).get("quiet"):
                    state["card"] = {"quiet": True, "card_id": card.get("id")}
            if t == "RUN_FINISHED" and isinstance(state.get("card"), dict) and not text:
                # a quiet card: the client applies it at once and the agent's next run says what was filled
                self._emit(state, {"type": "quiet", "card_id": state["card"].get("card_id")})
                state["answer"], state["card"], state["told"], state["spoke"] = [], False, {}, []
                return
            waits = state.get("waiting")
            # what the voice does not have yet: the answer without the sentences it was given on the way (a lead
            # taken back and written again is not said twice)
            told, spoke, by_id = state.get("told") or {}, set(state.get("spoke") or []), {}
            for m, d in state["answer"]:
                by_id[m] = by_id.get(m, "") + d
            rest = " ".join(x for x in _sentences(spoken(" ".join(body[told.get(m, 0):] for m, body in by_id.items())))
                            if x not in spoke)
            if t == "RUN_ERROR":
                rest = "Tell the person that something went wrong and to try again."
            elif waits:   # a card waits: the voice asks its question itself, and a spoken yes or no answers it
                rest = (rest + " " if rest else "") + asks(waits)
            elif not text and not spoke:
                rest = "Done. Tell the person it is done, in one short sentence."
            state["answer"], state["card"], state["told"], state["spoke"] = [], False, {}, []
            if rest:
                self._later(self._say(talk_id, rest))
            else:   # everything was said on the way
                state["pending"] = None
        elif t == "CUSTOM" and ev.get("name") == "on_interrupt":
            value = ev.get("value")
            if isinstance(value, str):
                try:
                    import json
                    value = json.loads(value)
                except ValueError:
                    value = {}
            quiet_card = isinstance(value, dict) and value.get("quiet")
            state["card"] = {"quiet": True, "card_id": value.get("card_id")} if quiet_card else True
            # a card that waits for the person: remembered until the next run starts, so a spoken yes or no can
            # answer it and silence does not end the conversation under it
            state["waiting"] = None if quiet_card else (value if isinstance(value, dict) and value else {"type": "set_fields"})
        elif t == "RUN_STARTED":
            state["waiting"] = None

    @staticmethod
    def _later(coro) -> None:
        import asyncio
        asyncio.ensure_future(coro)

    async def _say(self, talk_id: str, text: str, more: bool = False) -> None:
        """Give the voice a piece of the answer to say. `more`: the answer is still being written, so the
        request it belongs to stays open for the next piece."""
        import asyncio
        state = self._live.get(talk_id)
        if not state:
            return
        self._emit(state, {"type": "result", "text": text})
        # the answer belongs to the request the voice handed over; a typed message's answer belongs to none
        asked = state["pending"]
        if not more:
            state["pending"] = None
        try:
            async with state.setdefault("saying", asyncio.Lock()):   # pieces reach the voice in the order written
                await state["ws"].send(_json({"type": "session.commentary.append", "event_id": f"result_{secrets.token_hex(4)}",
                                              "delegation_id": asked, "content": text}))
        except Exception:  # noqa: BLE001
            await self.end(talk_id, "lost")

    async def events(self, talk_id: str):
        """What the client needs to know, as it happens: heard, spoken, result, error, ended."""
        state = self._live.get(talk_id)
        if not state:
            return
        while True:
            ev = await state["events"].get()
            if ev is None:
                return
            yield ev


HOSTS: list[Talks] = []   # the Talks of this process; the run routes report their events to them


def watch(talks: Talks) -> Talks:
    """Let these conversations hear the runs of their threads."""
    if talks not in HOSTS:
        HOSTS.append(talks)
    return talks


def active(thread_id: str) -> bool:
    """Whether a voice conversation is speaking this thread's answers right now. For tests of the voice branch
    without a paid session, VOICE_AS_IF=<prefix> on a test stand makes every thread with that prefix count."""
    as_if = os.environ.get("VOICE_AS_IF", "")
    if as_if and thread_id.startswith(as_if):
        return True
    # a form agent that answers inside a site conversation runs on its own thread, "<the conversation>-<form id>"
    return any(thread_id == t or thread_id.startswith(t + "-") for talks in HOSTS for t in list(talks._by_thread))


# a plain yes or no, in the product's seven languages (non-ASCII words as code points: the file stays ASCII)
_YES_WORDS = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "correct", "right", "confirm", "agree", "ja", "genau",
              "fine", "good", "great", "perfect", "set", "apply", "go", "ahead", "exactly", "put", "fill", "save",
              "enter", "true", "yea", "ya", "absolutely", "definitely", "indeed", _cyr(0x43f, 0x440, 0x430, 0x432, 0x434, 0x430), _cyr(0x430, 0x433, 0x430),
              _cyr(0x445, 0x43E, 0x440, 0x43E, 0x448, 0x43E),                                # "khorosho"
              _cyr(0x447, 0x451, 0x442, 0x43A, 0x43E), _cyr(0x447, 0x435, 0x442, 0x43A, 0x43E),      # "chyotko"
              _cyr(0x441, 0x442, 0x430, 0x432, 0x44C), _cyr(0x434, 0x430, 0x432, 0x430, 0x439),      # "stav'", "davai"
              _cyr(0x442, 0x43E, 0x447, 0x43D, 0x43E), _cyr(0x43F, 0x43E, 0x434, 0x442, 0x432, 0x435, 0x440, 0x436, 0x434, 0x430, 0x44E),
              "oui", "si", "s" + chr(0xED), "s" + chr(0xEC), "claro", "certo",
              "".join(map(chr, (0x434, 0x430))), "".join(map(chr, (0x430, 0x433, 0x430))),
              "".join(map(chr, (0x442, 0x430, 0x43A))), "".join(map(chr, (0x432, 0x435, 0x440, 0x43D, 0x43E))),
              "".join(map(chr, (0x43A, 0x43E, 0x43D, 0x435, 0x447, 0x43D, 0x43E))),
              "".join(map(chr, (0x445, 0x43E, 0x440, 0x43E, 0x448, 0x43E))),
              "".join(map(chr, (0x441, 0x43E, 0x433, 0x43B, 0x430, 0x441, 0x435, 0x43D)))}
_NO_WORDS = {"no", "nope", "nah", "cancel", "wrong", "nein", "non", "not",
             "".join(map(chr, (0x43D, 0x435, 0x442))), "".join(map(chr, (0x43D, 0x456))),
             "".join(map(chr, (0x43D, 0x435)))}
_FILLERS = {"uh", "um", "please", "do", "it", "that", "is", "thanks", "thank", "you", "i", "said", "the", "bitte",
            "but", "say", "all", "looks", "its", "s", "them", "this", "everything", "in", "then", "so", "and", "just",
            "now", "there", "well", "oh", "one", "of", "course",
            "".join(map(chr, (0x43F, 0x43E, 0x436, 0x430, 0x43B, 0x443, 0x439, 0x441, 0x442, 0x430))),
            "".join(map(chr, (0x432, 0x441, 0x451))), "".join(map(chr, (0x432, 0x441, 0x435)))}


# words that give an order rather than agree ("set it" is a yes; "set the term to five years" is a request), and
# words that turn a yes into something else: a new value, another request, a question
_ORDERS = {"set", "apply", "go", "ahead", "put", "fill", "save", "enter", "fine", "good", "great", "perfect",
           _cyr(0x441, 0x442, 0x430, 0x432, 0x44C), _cyr(0x434, 0x430, 0x432, 0x430, 0x439)}
_TURNS = {"to", "for", "change", "different", "another", "other", "wait", "actually", "instead", "rather", "make",
          "except", "also", "add", "remove", "plus", "what", "how", "when", "where", "which", "who", "can", "could",
          "maybe", "unless"}
_DELEGATES = re.compile(
    r"\b((do(es)?n'?t|do(es)? not) (care|matter)|whatever|up to you|you (choose|pick|decide|select)"
    r"|(just )?(pick|select|choose|take) (something|anything|any|one|whichever)|any of (them|those)|either( one)?)\b"
    r"|\u043a\u0430\u043a \u0445\u043e\u0447\u0435\u0448\u044c|\u0432\u044b\u0431\u0435\u0440\u0438 \u0441\u0430\u043c|\u0432\u044b\u0431\u0438\u0440\u0430\u0439 \u0441\u0430\u043c|\u0432\u0441\u0451 \u0440\u0430\u0432\u043d\u043e|\u0432\u0441\u0435 \u0440\u0430\u0432\u043d\u043e|\u0431\u0435\u0437 \u0440\u0430\u0437\u043d\u0438\u0446\u044b|\u043d\u0430 \u0442\u0432\u043e\u0439 \u0432\u044b\u0431\u043e\u0440|\u043d\u0430 \u0442\u0432\u043e\u0451 \u0443\u0441\u043c\u043e\u0442\u0440\u0435\u043d\u0438\u0435|\u043b\u044e\u0431\u043e\u0439|\u043b\u044e\u0431\u0443\u044e|\u043b\u044e\u0431\u043e\u0435|\u044f\u043a \u0445\u043e\u0447\u0435\u0448|\u043e\u0431\u0435\u0440\u0438 \u0441\u0430\u043c|\u0431\u0430\u0439\u0434\u0443\u0436\u0435|\u0431\u0443\u0434\u044c-\u044f\u043a\u0438\u0439|\u0431\u0443\u0434\u044c-\u044f\u043a\u0443",
    re.IGNORECASE)


def delegates(text: str | None) -> bool:
    """Whether the person left the choice to the assistant ("I don't care, just select something", "up to you")."""
    return bool(_DELEGATES.search(text or ""))


def named(card: dict, asked: str | None) -> bool:
    """Whether a text names every value of a field-change card: the assistant's own question ("Just to be sure: is
    the loan amount 5 million?") that the person has just said yes to. A consent is never named this way."""
    rows = card.get("changes") if isinstance(card, dict) else None
    if not rows or card.get("type") not in (None, "set_fields") or not (asked or "").strip():
        return False
    numbers = said_numbers(asked or "")
    return all(isinstance(r, dict) and not r.get("consent") and not r.get("issue") and _was_said(r, asked or "", numbers)
               for r in rows)


def yes_or_no(text: str) -> bool | None:
    """True for a plain yes, False for a plain no, None for anything else. Plain means eight words at most and
    nothing but the yes or no and filler ("yes please", "I said yes", "no thanks"); "yes, but make it 48" is a
    request, and both words together are neither. A longer utterance is a yes when it opens with agreement and
    holds no figure, no refusal and no turn to something else."""
    words = re.findall(_LETTERS, (text or "").lower())
    # a figure in it is a new value, not a yes ("oh" and "one" are not figures here: "oh yes", "this one")
    if not words or len(words) > 14 or any(n not in ("0", "1") for n in said_numbers(text or "")):
        return None
    yes, no = any(w in _YES_WORDS for w in words), any(w in _NO_WORDS for w in words)
    rest = [w for w in words if w not in _YES_WORDS and w not in _NO_WORDS and w not in _FILLERS]
    if len(words) <= 8 and not rest and yes != no:
        return yes
    # an utterance that opens with agreement and turns to nothing else is a yes, whatever comes with it ("Yeah, I
    # said, set it. Set value", "Yeah, set it, why you didn't set"): the person is repeating themselves
    opens = next((w for w in words if w not in _FILLERS), "")
    if opens in _YES_WORDS and opens not in _ORDERS and not no and not any(w in _TURNS for w in words):
        return True
    return None


def same_changes(one: list | None, other: list | None) -> bool:
    """Whether two cards propose the same values for the same fields (a consent is never the same: it is asked)."""
    def key(rows: list | None) -> list:
        return sorted((str(r.get("name")), _json({"v": r.get("value")})) for r in rows or [] if isinstance(r, dict))
    if not one or not other or any(isinstance(r, dict) and r.get("consent") for r in [*one, *other]):
        return False
    return key(one) == key(other)


def asks(card: dict) -> str:
    """What the voice is given to say when a card waits for the person: the card's own question, to be answered
    aloud with yes or no. Never a pointer to the screen."""
    kind = card.get("type") or "set_fields"
    # the text is what the voice says (it paraphrases, in the person's language), so it is the question itself
    if kind == "ask":
        options = [str(o.get("label") or o.get("id")) for o in card.get("options") or [] if isinstance(o, dict)][:5]
        return f"{card.get('question') or 'Which one?'}" + (f" The choices are: {', '.join(options)}." if options else "")
    if kind == "confirm":
        return f"{card.get('title') or card.get('message') or 'Shall I go ahead?'} Say yes or no."
    rows = [f"{r.get('label') or r.get('name')}: {r.get('display') or r.get('value')}"
            for r in card.get("changes") or [] if isinstance(r, dict)][:4]
    if not rows:
        return "Shall I fill that in? Say yes or no."
    if any(isinstance(r, dict) and spelled(r) for r in card.get("changes") or []):
        # a name or an e-mail as it was heard: read back, with a way out when it was heard wrong
        return "I heard " + " and ".join(rows) + ". Is that right? If not, spell it for me."
    return "Shall I fill in " + " and ".join(rows) + "? Say yes or no."


ECHO_SECONDS = 15.0   # how long after the voice spoke its own words can come back
ECHO_WORDS = 4        # a shorter text is never dropped: "Car loan" after "A car loan or a home loan?" is an answer


def is_echo(heard: str, said: list, now: float | None = None) -> bool:
    """Whether what was heard is the voice's own speech picked up by the microphone: four words or more that are,
    word for word, a run of what the voice said in the last seconds (`said`: (monotonic time, text) pieces)."""
    words = re.findall(_LETTERS + r"|\d+", (heard or "").lower())
    if len(words) < ECHO_WORDS:
        return False
    now = time.monotonic() if now is None else now
    recent = " ".join(text for at, text in said if now - at <= ECHO_SECONDS)
    spoken_words = re.findall(_LETTERS + r"|\d+", recent.lower())
    n = len(words)
    return any(spoken_words[i:i + n] == words for i in range(len(spoken_words) - n + 1))


ALOUD = ("\n\n[The person is talking to you by voice and will HEAR your answer. Answer in one or two short spoken "
         "sentences: no lists, no markup, no headings, no \"still open\" inventory. Say what you did and, at most, the "
         "one next thing. Their words reached you through speech recognition: a filler word or an odd spelling is "
         "not part of the value. A last name, a company name or an e-mail may have been heard wrong: propose "
         "it as you heard it (it is read back to them), and when they spell it letter by letter, join the letters "
         "into the word and propose that. Propose only what they said or clearly named; when a field would need a guess "
         "(new or used, which of several options), do not propose it: ask for it in one short question.]")


def heard_as(message: str | None, aloud: bool) -> str | None:
    """The message as the model reads it in a voice conversation: with the note that the answer is spoken. The
    conversation's record keeps the person's words alone."""
    return message + ALOUD if aloud and message else message


# ---------------------------------------------------------------- filling quietly: what the person said needs no card

_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_UNITS["oh"] = 0
_TENS = {w: (i + 2) * 10 for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}


# how people shorten a number aloud: "50k", "1.5 million", "one and a half million", "half a million", and the same
# in Russian (the words are built from code points: the file stays ASCII)
_THOUSAND = "(?:k|thousand|" + _cyr(0x43A) + "|" + _cyr(0x442, 0x44B, 0x441) + r"\w*)"
_MILLION = "(?:m|mln|million|" + _cyr(0x43C, 0x43B, 0x43D) + "|" + _cyr(0x43C, 0x438, 0x43B, 0x43B, 0x438, 0x43E, 0x43D) + r"\w*)"
_ONE_HALF = "(?:one and a half|" + _cyr(0x43F, 0x43E, 0x43B, 0x442, 0x43E, 0x440) + "[" + _cyr(0x430, 0x44B) + "])"
_SHORT = [(re.compile(r"(\d+(?:[.,]\d+)?)\s*" + _MILLION + r"\b"), 1_000_000),
          (re.compile(r"(\d+(?:[.,]\d+)?)\s*" + _THOUSAND + r"\b"), 1000)]


def _short_numbers(text: str) -> str:
    """The text with shortened numbers written out in digits: "50k" 50000, "1.5 million" 1500000, "one and a half
    million" 1500000, "half a million" 500000."""
    text = re.sub(_ONE_HALF + r"\s+" + _MILLION + r"\b", "1500000", text)
    text = re.sub(_ONE_HALF + r"\s+" + _THOUSAND + r"\b", "1500", text)
    text = re.sub(r"half a\s+" + _MILLION + r"\b", "500000", text)
    for pattern, times in _SHORT:
        text = pattern.sub(lambda m, times=times: str(int(round(float(m.group(1).replace(",", ".")) * times))), text)
    return text


def said_numbers(text: str) -> list[str]:
    """The numbers in what was said, in order, as digit strings: digits as written ("93", "2015-06-10" gives
    2015, 06, 10) and English number words ("ninety-three" 93, "four four three four" 4, 4, 3, 4, "five hundred
    thousand" 500000). A word that cannot continue the number before it starts a new one."""
    out: list[str] = []
    total = current = 0
    open_ = False        # a number is being read
    last = ""            # what the last word was: unit, teen, tens, hundred, scale

    def flush() -> None:
        nonlocal total, current, open_, last
        if open_:
            out.append(str(total + current))
        total = current = 0
        open_, last = False, ""

    for word in re.findall(r"[a-z]+|\d+", _short_numbers((text or "").lower())):
        if word == "k" and open_:   # "two hundred k"
            word = "thousand"
        if word.isdigit():
            flush()
            out.append(word)
        elif word in _UNITS:
            n = _UNITS[word]
            fits = open_ and n < 10 and last == "tens"          # "ninety" then "two"
            fits = fits or (open_ and last in ("hundred", "scale"))   # "five hundred" then "three"
            if not fits:
                flush()
            current += n
            open_, last = True, "unit" if n < 10 else "teen"
        elif word in _TENS:
            if not (open_ and last in ("hundred", "scale")):
                flush()
            current += _TENS[word]
            open_, last = True, "tens"
        elif word in _SCALES and open_:
            if word == "hundred":
                current, last = (current or 1) * 100, "hundred"
            else:
                total, current, last = total + (current or 1) * _SCALES[word], 0, "scale"
        elif word == "and" and open_ and last in ("hundred", "scale"):
            continue
        else:
            flush()
    flush()
    return out


# words in Latin (with accents) and Cyrillic letters; the ranges are built from code points, the file stays ASCII
_LETTERS = "[a-z" + chr(0xC0) + "-" + chr(0x24F) + chr(0x400) + "-" + chr(0x4FF) + "]+"


def _was_said(row: dict, said: str, numbers: list[str]) -> bool:
    """Whether the value of this row is in the person's own words: every word of it was said, or its digits are
    among the numbers they said (alone, or as a run of them: "four four three four" for 4434)."""
    value = row.get("value")
    names = [row.get("display"), value.get("name") if isinstance(value, dict) else value]
    words_said = set(re.findall(_LETTERS, (said or "").lower()))
    stream = "".join(numbers)
    for candidate in (str(c) for c in names if c not in (None, "", [], {}) and not isinstance(c, (dict, list, bool))):
        digits = re.sub(r"\D", "", candidate)
        words = [w for w in re.findall(_LETTERS, candidate.lower()) if len(w) > 1]
        if digits:
            # a number carries the value; the words beside it are its unit ("36 months" for a spoken "36")
            if digits in numbers or (len(digits) > 1 and digits in stream) or digits.lstrip("0") in numbers:
                return True
        elif words:
            # the field's own words are not the choice: "for my car" names "Car loan" of the field "Loan type". Every
            # other word of the value must have been said, so "New car" is not named by "for my car".
            own = {w.rstrip("s") for w in re.findall(_LETTERS, str(row.get("label") or "").lower())}
            names_it = [w for w in words if w.rstrip("s") not in own] or words
            if all(w in words_said or w.rstrip("s") in words_said or w + "s" in words_said for w in names_it):
                return True
    return False


def quiet(card: dict, said: str | None) -> bool:
    """Whether a field-change card may be applied without being shown, in a voice conversation: every row is a
    value the person said, goes into a field that was empty, and is neither a consent nor spelled data (a last
    name, a company name, an e-mail: see `spelled`). Anything else is confirmed on a card: a consent, a value the person did not say, a
    value that replaces another, a name that may have been misheard."""
    rows = card.get("changes") if isinstance(card, dict) else None
    if not rows or card.get("type") not in (None, "set_fields") or not (said or "").strip():
        return False
    numbers = said_numbers(said or "")
    for row in rows:
        if not isinstance(row, dict) or row.get("consent") or row.get("issue"):
            return False
        if row.get("previous") not in (None, "", [], {}):
            return False
        if spelled(row):
            return False
        if not _was_said(row, said or "", numbers):
            return False
    return True


_SPELLED = re.compile(
    r"last[ _-]?name|surname|family[ _-]?name|company|employer|organi[sz]ation|business[ _-]?name|e-?mail|nachname|familienname|firma|arbeitgeber|apellido|empresa|nom de famille|soci\u00e9t\u00e9|entreprise|cognome|azienda|\u0444\u0430\u043c\u0438\u043b\u0438|\u043a\u043e\u043c\u043f\u0430\u043d\u0438|\u043e\u0440\u0433\u0430\u043d\u0438\u0437\u0430\u0446\u0438|\u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b|\u043f\u043e\u0447\u0442|\u043f\u0440\u0456\u0437\u0432\u0438\u0449|\u043a\u043e\u043c\u043f\u0430\u043d\u0456|\u043e\u0440\u0433\u0430\u043d\u0456\u0437\u0430\u0446\u0456|\u0440\u043e\u0431\u043e\u0442\u043e\u0434\u0430\u0432|\u043f\u043e\u0448\u0442",
    re.IGNORECASE)


def spelled(row: dict) -> bool:
    """Whether a row holds a word speech recognition gets wrong and a mistake in which is costly: a last name, a
    company name or an e-mail (by the field's name or label, or an @ in the value). These are read back and never
    filled quietly; a first name, a number, a date and an option of a list the person said are filled."""
    value = row.get("value")
    if row.get("kind") != "text" or not isinstance(value, str) or not re.search(_LETTERS, value.lower()):
        return False
    return "@" in value or bool(_SPELLED.search(f"{row.get('name') or ''} {row.get('label') or ''}"))


def seen(thread_id: str, ev: dict) -> None:
    """Called by the run routes for every event they send. Costs a list check when no host has voice."""
    for talks in HOSTS:
        talks.seen(thread_id, ev)


class Refused(Exception):
    """A conversation may not start: `busy`, `day` or `person_day`."""


def _json(value: dict) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


class UnlockIn(BaseModel):
    code: str


class StartIn(BaseModel):
    sdp: str
    thread_id: str


class EndIn(BaseModel):
    talk: str


def create_voice_router(talks: Talks):
    """The voice routes of a host. Mount them only when `talks.config.enabled`: without a code there is no mode.
        POST /unlock   {code}                      -> {person, pass}            403 for a wrong code
        POST /session  {sdp, thread_id}  + pass    -> {talk, sdp, limits}       429 {reason} when it may not start
        GET  /events?talk=             + pass    -> a stream of what is heard and said (SSE)
        POST /end      {talk}            + pass    -> {cost_usd}: what the conversation cost
    The pass travels in the X-Voice-Pass header, never in an address."""
    if APIRouter is None:
        raise ImportError("the voice routes need: pip install 'formguide[server]'")
    from . import agui

    r = APIRouter()

    def who(request: Request) -> str:
        person = talks.who(request.headers)
        if not person:
            raise HTTPException(403, "A voice pass is needed.")
        return person

    @r.post("/unlock")
    def unlock(body: UnlockIn, request: Request) -> dict:
        got = talks.gate.unlock(body.code, request.client.host if request.client else "?")
        if not got:
            raise HTTPException(403, "That code does not open the voice mode.")
        return {"person": got[0], "pass": got[1]}

    @r.post("/session")
    async def session(body: StartIn, request: Request) -> dict:
        person = who(request)
        try:
            return await talks.start(person, body.sdp, body.thread_id)
        except Refused as e:
            raise HTTPException(429, {"reason": str(e)}) from None
        except Exception as e:  # noqa: BLE001 - the provider is down or refused: a reason, never a trace
            raise HTTPException(502, f"The voice is unavailable right now ({type(e).__name__}).") from None

    @r.get("/events")
    async def events(talk: str, request: Request) -> StreamingResponse:
        person = who(request)
        open_talk = talks.meter.open.get(talk)
        if not open_talk or open_talk.person != person:
            raise HTTPException(404, "No such conversation.")

        async def body():
            async for ev in talks.events(talk):
                yield f"data: {_json(ev)}\n\n"
        return StreamingResponse(agui.alive(body()), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @r.post("/end")
    async def end(body: EndIn, request: Request) -> dict:
        person = who(request)
        open_talk = talks.meter.open.get(body.talk)
        cost = await talks.end(body.talk, "closed") if open_talk and open_talk.person == person else 0.0
        return {"cost_usd": round(cost, 4)}

    @r.websocket("/stream")
    async def stream(socket: WebSocket, thread_id: str) -> None:
        """One socket for a client whose audio passes through this server (a native app, a test runner).
            the pass: the X-Voice-Pass header of the opening request
            client -> server   binary frames: microphone audio, raw PCM16 mono 24 kHz, in real time
                               a text frame {"type": "end"}: the person ended the conversation
            server -> client   binary frames: the voice's audio, the same format
                               text frames: {"type": "started", talk, limits, audio}, then the events of
                               GET /events (hearing, heard, spoken, result, quiet, echo, error, ended)
        A refusal is one text frame {"type": "refused", "reason"} and the socket closes: `pass` for no pass, or
        busy, day, person_day, unavailable. On `heard` the client sends the ordinary run, as on the web."""
        import asyncio
        await socket.accept()
        person = talks.who(socket.headers)
        if not person:
            await socket.send_text(_json({"type": "refused", "reason": "pass"}))
            return await socket.close(code=4403)
        try:
            opened = await talks.start_stream(person, thread_id)
        except Refused as e:
            await socket.send_text(_json({"type": "refused", "reason": str(e)}))
            return await socket.close(code=4429)
        except Exception:  # noqa: BLE001 - the provider is down or refused
            await socket.send_text(_json({"type": "refused", "reason": "unavailable"}))
            return await socket.close(code=4502)
        talk = opened["talk"]
        await socket.send_text(_json({"type": "started", **opened}))

        async def events_out() -> None:
            async for ev in talks.events(talk):
                await socket.send_text(_json(ev))

        async def audio_out() -> None:
            async for piece in talks.audio(talk):
                await socket.send_bytes(piece)

        out = [asyncio.create_task(events_out()), asyncio.create_task(audio_out())]
        try:
            while talk in talks.meter.open:
                message = await socket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if message.get("bytes"):
                    await talks.feed(talk, message["bytes"])
                elif message.get("text") and '"end"' in message["text"]:
                    break
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await talks.end(talk, "closed")
            await asyncio.gather(*out, return_exceptions=True)
            try:
                await socket.close()
            except Exception:  # noqa: BLE001 - the client has gone
                pass

    return r
