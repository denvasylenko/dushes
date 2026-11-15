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
        elif not talk.seconds:
            talk.seconds = self.now() - talk.started
        cost = talk.seconds / 60 * self.config.minute_usd + talk.agent_usd
        self._spent[talk.person] = self._spent.get(talk.person, 0.0) + cost
        return cost
