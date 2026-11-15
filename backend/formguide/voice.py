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

from pydantic import BaseModel

try:   # the routes need the HTTP layer; Gate, Meter and Talks do not
    from fastapi import APIRouter, HTTPException, Request
    from fastapi.responses import StreamingResponse
except ImportError:  # pragma: no cover
    APIRouter = HTTPException = Request = StreamingResponse = None  # type: ignore[assignment,misc]

_NAME = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
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
    at_once: int = 1                # voice conversations at the same time
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

    def person(self, token: str | None) -> str | None:
        """Whose pass this is, or None: malformed, signed by another secret, expired, or its code was withdrawn."""
        parts = (token or "").split(".")
        if len(parts) != 3:
            return None
        name, expiry, signature = parts
        if not hmac.compare_digest(signature, self._sign(f"{name}.{expiry}")):
            return None
        if not expiry.isdigit() or int(expiry) < self.now() or name not in self.config.codes:
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

    def __init__(self, config: VoiceConfig, now: Callable[[], float] = time.time):
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
        closed = self._spent.get(person, 0.0) if person else sum(self._spent.values())
        return closed + sum(self.cost(t) for t in self.open.values() if not person or t.person == person)

    def refusal(self, person: str) -> str | None:
        """Why a new conversation may not start now: `busy`, `day` or `person_day`; None when it may."""
        if len(self.open) >= self.config.at_once:
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


class Talks:
    """The voice conversations of one host: who may start one, what each hears and says, when each ends."""

    def __init__(self, config: VoiceConfig, *, title: str = "this site", key: Callable[[], str] | None = None,
                 opener: Callable | None = None, now: Callable[[], float] = time.time,
                 log_dir: str | os.PathLike | None = None):
        # a conversation is recorded when log_dir is given: one JSON line an event (what was heard, what the voice
        # said, the answers handed to it, the clock, the end and its cost), in <log_dir>/<day>_<talk>.jsonl
        self.log_dir = log_dir
        self.config = config
        self.gate = Gate(config, now)
        self.meter = Meter(config, now)
        self.title = title
        self._key = key or (lambda: os.environ.get("OPENAI_API_KEY", ""))
        self._opener = opener or open_live     # tests give a scripted one
        self.now = now
        self._live: dict[str, dict] = {}       # talk id -> its state
        self._by_thread: dict[str, str] = {}   # the chat thread -> the talk that speaks its answers

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
        return {"talk": talk.id, "sdp": answer,
                "limits": {"seconds": self.config.max_seconds, "silence_seconds": self.config.silence_seconds}}

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
                if t == "session.input_transcript.delta":
                    state["heard"] += ev.get("delta", "")
                    self.meter.report(talk_id, heard=True)
                    self._emit(state, {"type": "hearing", "delta": ev.get("delta", "")})   # their words, as they speak
                elif t == "session.delegation.created":   # the voice wants the agent: hand over what was said
                    text, state["heard"] = state["heard"].strip(), ""
                    state["pending"] = (ev.get("delegation") or {}).get("id")
                    state["answer"] = []
                    if text:
                        self._emit(state, {"type": "heard", "text": text})
                elif t == "session.output_transcript.delta":
                    self.meter.report(talk_id, heard=True)   # the conversation is alive while the voice speaks
                    self._emit(state, {"type": "spoken", "delta": ev.get("delta", "")})
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
        if t == "TEXT_MESSAGE_CONTENT":
            state["answer"].append((ev.get("messageId"), ev.get("delta", "")))
        elif t == "CUSTOM" and ev.get("name") == "text_retract":
            gone = (ev.get("value") or {}).get("messageId")
            state["answer"] = [(m, d) for m, d in state["answer"] if m != gone]
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
                state["answer"], state["card"] = [], False
                return
            waits = bool(((ev.get("outcome") or {}).get("interrupts"))) or state.get("card")
            if t == "RUN_ERROR":
                text = "Tell the person that something went wrong and to try again."
            elif not text:
                text = ("A card is on the screen: ask the person to confirm it there." if waits
                        else "Done. Tell the person it is done, in one short sentence.")
            state["answer"], state["card"] = [], False
            import asyncio
            asyncio.ensure_future(self._say(talk_id, text))
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

    async def _say(self, talk_id: str, text: str) -> None:
        state = self._live.get(talk_id)
        if not state:
            return
        self._emit(state, {"type": "result", "text": text})
        # the answer belongs to the request the voice handed over; a typed message's answer belongs to none
        asked, state["pending"] = state["pending"], None
        try:
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
    """Whether a voice conversation is speaking this thread's answers right now."""
    return any(thread_id in talks._by_thread for talks in HOSTS)


ALOUD = ("\n\n[The person is talking to you by voice and will HEAR your answer. Answer in one or two short spoken "
         "sentences: no lists, no markup, no headings, no \"still open\" inventory. Say what you did and, at most, the "
         "one next thing. Their words reached you through speech recognition: a filler word or an odd spelling is "
         "not part of the value. Propose only what they said or clearly named; when a field would need a guess "
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

    for word in re.findall(r"[a-z]+|\d+", (text or "").lower()):
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
    value the person said, goes into a field that was empty, and is not a consent. Anything else is confirmed on
    a card: a consent, a value the person did not say, a value that replaces another."""
    rows = card.get("changes") if isinstance(card, dict) else None
    if not rows or card.get("type") not in (None, "set_fields") or not (said or "").strip():
        return False
    numbers = said_numbers(said or "")
    for row in rows:
        if not isinstance(row, dict) or row.get("consent") or row.get("issue"):
            return False
        if row.get("previous") not in (None, "", [], {}):
            return False
        if not _was_said(row, said or "", numbers):
            return False
    return True


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
        person = talks.gate.person(request.headers.get("x-voice-pass"))
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

    return r
