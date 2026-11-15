"""Voice benchmark: recorded clips speak, the voice mode answers, code checks the result. Design: evals/voice/README.md.

    uv run python scripts/voice_bench.py --mock                       # no session, no key, no money: the plumbing
    uv run python scripts/voice_bench.py --mock voice_fill_toyota     # one scenario
    uv run python scripts/voice_bench.py --live --base http://127.0.0.1:8097 --max-usd 1.40   # real sessions (the owner's yes)

A scenario (evals/voice/*.yaml) is a chat scenario whose scripted lines are spoken: each line is a clip recorded once
by scripts/voice_clips.py with the Mac's own voice. Nothing here calls a model to play the person.

Two bridges:
  --mock   a scripted voice in this process: it "hears" the clip's own text, runs the ordinary Dushes turn on an
           offline demo (a one-line model), and "speaks" the first sentence of the reply. Times are those of this
           process, the voice's delays are fixed numbers. It proves the runner, the scenarios, the checks and the
           report; its task results say nothing about the product.
  --live   formguide.voice over its one WebSocket (GET <host>/voice/stream, the socket a native app uses): the clip
           goes in as a microphone would send it, the voice's audio and the conversation's events come back, and on
           every "heard" the runner posts the ordinary chat run in the same thread, as the widget does. It needs a
           host with voice on (--base) and one of its codes in VOICE_BENCH_CODE (a test code of your own stand, in
           the environment, never in a file). A paid voice run needs the owner's yes with a price and a stop sum.

Measured per spoken line: what was heard against what was said (word error rate; numbers and names exactly), the
time from the end of speech to the first sound, to the first step on screen and to the first useful sentence; for an
interruption, the time to silence and whether the turn in progress was cancelled. Per scenario: the same code checks
as chat (fields, the page reached, stays_put_on, cards, never_says). Per run: connected seconds, dollars for the voice
and for the agent, per task and per minute.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
SCENARIOS = HERE / "evals" / "voice"
RUNS = Path(__file__).parent / "runs"
CLIPS = RUNS / "voice-clips"
OPEN_SECONDS = 15          # the least a session is billed (gpt-live-1: 15 s at opening, credited against its own duration; not a surcharge)
SILENCE_AFTER = 0.8        # seconds of silence the runner sends after a clip, for the session's end-of-speech detection


@dataclass
class Turn:
    """One spoken line and what came back."""
    said: str
    heard: str = ""
    spoken: str = ""
    clip_seconds: float = 0.0
    first_sound_s: float | None = None     # from the end of speech to the first audible sample
    first_step_s: float | None = None      # ... to the first event of the Dushes turn on screen
    useful_s: float | None = None          # ... to the start of the first sentence that carries the answer
    cut_in: bool = False                   # this line was spoken over the assistant
    silence_s: float | None = None         # for a cut-in: from its start to the assistant falling silent
    cancelled: bool | None = None          # for a cut-in: the turn in progress was stopped
    error: str | None = None


@dataclass
class Session:
    turns: list[Turn] = field(default_factory=list)
    connected_s: float = 0.0
    visit: Any = None                      # the chat-side view of the same conversation: the checks read it
    cost_usd: float | None = None          # live: what the host says the conversation cost (voice seconds and the agent's turns)
    line: Any = None                       # live: the open socket


# ===================================================================== what was heard


def words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", text.lower())


def wer(said: str, heard: str) -> float:
    """Word error rate: the edit distance between the words said and the words heard, over the words said."""
    a, b = words(said), words(heard)
    if not a:
        return 0.0 if not b else 1.0
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return round(row[-1] / len(a), 3)


def entities(text: str) -> list[str]:
    """What must be heard exactly: numbers, and words written with a capital inside a sentence (names, codes)."""
    caps = [w for i, w in enumerate(re.findall(r"[^\W\d_][\w'-]*", text)) if i and w[0].isupper()]
    return re.findall(r"\d+(?:[.,]\d+)?", text) + caps


def entities_kept(said: str, heard: str) -> tuple[int, int]:
    want = entities(said)
    low = heard.lower()
    return sum(1 for e in want if e.lower() in low), len(want)


# ===================================================================== sound (for the live bridge)
# What the model check of gpt-live-1 taught (Owner, 2026-11-15): the session sends audio frames all the time, silence
# included, so "the first sound" is found by level, never by the first audio event; audio goes in at real-time pace in
# 100 ms pieces, or it is not taken as a microphone; and nothing says "the assistant finished speaking", so a turn ends
# after END_OF_TURN seconds without sound.

SAMPLE_RATE = 24000
CHUNK = SAMPLE_RATE * 2 // 10      # 100 ms of 16-bit mono
LOUD = 800                         # a sample above this is sound, below it the line's own noise
END_OF_TURN = 3.0


def pcm_of(wav: Path) -> bytes:
    """A clip's samples without the WAV header: raw PCM 16-bit mono 24 kHz, what the session takes."""
    import wave
    with wave.open(str(wav)) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"{wav.name}: {w.getframerate()} Hz, {w.getnchannels()} ch, {8 * w.getsampwidth()} bit; the session takes 24 kHz mono 16 bit")
        return w.readframes(w.getnframes())


def pieces(pcm: bytes, lead_silence: float = 0.5, tail_silence: float = SILENCE_AFTER) -> list[bytes]:
    """The clip as the microphone would send it: 100 ms pieces, a little silence before and after."""
    quiet = b"\x00" * CHUNK
    body = [pcm[i:i + CHUNK] for i in range(0, len(pcm) - len(pcm) % 2, CHUNK)]
    return [quiet] * round(lead_silence * 10) + body + [quiet] * round(tail_silence * 10)


def is_sound(pcm: bytes, level: int = LOUD) -> bool:
    return any(abs(int.from_bytes(pcm[i:i + 2], "little", signed=True)) > level for i in range(0, len(pcm) - 1, 2))


def sound_times(frames: list[tuple[float, bytes]], since: float) -> dict[str, float | None]:
    """From the frames that came back (time, pcm): when the first sound came after `since`, when the last sound was,
    and when the sound started again after a pause (the returned result spoken, after the voice's own "one moment")."""
    loud = [t for t, pcm in frames if t >= since and is_sound(pcm)]
    again = next((b for a, b in zip(loud, loud[1:]) if b - a > 0.6), None)
    return {"first": round(loud[0] - since, 2) if loud else None, "last": round(loud[-1] - since, 2) if loud else None,
            "again": round(again - since, 2) if again is not None else None}


def turn_over(last_sound: float | None, now: float, answered: float | None) -> bool:
    """A turn is over when the result was handed to the voice and nothing has sounded for END_OF_TURN seconds."""
    return answered is not None and last_sound is not None and now - last_sound > END_OF_TURN and last_sound >= answered


# ===================================================================== the bridges


class MockBridge:
    """A scripted voice over an offline demo: hears the clip's text, runs the Dushes turn, speaks its first sentence."""
    name = "mock"
    FIRST_SOUND, SPEAK_AFTER_RESULT = 0.35, 0.25   # fixed stand-ins for the voice model's own delays, seconds

    def __init__(self, tmp: Path, garble: bool = False):
        import evals
        self.http = evals.offline_client(tmp)
        self.garble = garble

    def open(self, sc: Any) -> Session:
        import evals
        from harness_client import Visit
        visit = Visit(self.http, sc.page, answer=evals.RuleGuest(sc).choose, site=sc.site)
        visit.ticks = set()              # by voice no consent is ever ticked: a tick is a tap
        if sc.values and visit.form:
            visit.form.apply(sc.values)
        return Session(visit=visit, connected_s=0.0)

    def say(self, s: Session, clip: dict, cut_in: bool, then_cut_in: bool = False) -> Turn:
        t = Turn(said=clip["text"], clip_seconds=float(clip.get("seconds") or 0), cut_in=cut_in)
        t.heard = re.sub(r"\d", "0", clip["text"]) if self.garble else clip["text"]
        before = len(s.visit.replies)
        t0 = time.perf_counter()
        try:
            s.visit.say(t.heard)
        except Exception as e:  # noqa: BLE001
            t.error = f"{type(e).__name__}: {e}"[:200]
        took = time.perf_counter() - t0
        new = [text for _mid, text in s.visit.replies[before:]]
        t.spoken = re.split(r"(?<=[.!?])\s", " ".join(new).strip(), maxsplit=1)[0] if new else ""
        t.first_sound_s, t.first_step_s = self.FIRST_SOUND, round(min(took, 0.05), 3)
        t.useful_s = round(took + self.SPEAK_AFTER_RESULT, 3) if t.spoken else None
        if cut_in:
            t.silence_s, t.cancelled = 0.2, True
        s.connected_s += t.clip_seconds + SILENCE_AFTER + took + 2.0   # the clip, its silence, the turn, the answer aloud
        s.turns.append(t)
        return t

    def close(self, s: Session) -> None:
        s.visit.finish()


class StopSum(Exception):
    """The stop sum is reached: no more sessions are opened."""


class Line:
    """One open /voice/stream socket: a thread reads what comes back (events and audio, each with this process's
    clock), another sends a 100 ms piece every 100 ms, the clip's while one plays and silence otherwise, so the
    socket is a live microphone from the first moment to the last."""

    def __init__(self, ws: Any):
        import queue
        import threading
        self.ws, self.t0 = ws, time.monotonic()
        self.events: list[tuple[float, dict]] = []
        self.frames: list[tuple[float, bytes]] = []
        self._out: Any = queue.Queue()
        self.alive = True
        self.marks: dict[str, float] = {}
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._feed, daemon=True).start()

    def now(self) -> float:
        return time.monotonic() - self.t0

    def _read(self) -> None:
        try:
            for m in self.ws:
                if isinstance(m, bytes):
                    self.frames.append((self.now(), m))
                else:
                    self.events.append((self.now(), json.loads(m)))
        except Exception:  # noqa: BLE001 - the socket closed
            pass
        self.alive = False

    def _feed(self) -> None:
        import queue
        due = time.monotonic()
        while self.alive:
            try:
                piece, mark = self._out.get_nowait()
            except queue.Empty:
                piece, mark = b"\x00" * CHUNK, None
            try:
                self.ws.send(piece)
            except Exception:  # noqa: BLE001
                break
            if mark:
                self.marks[mark] = self.now()
            due += 0.1
            time.sleep(max(0.0, due - time.monotonic()))

    def speak(self, pcm: bytes, tag: str) -> tuple[float, float]:
        """Plays a clip into the socket at real-time pace; returns when its last piece went: (start, end)."""
        body = pieces(pcm, 0, 0)
        for n, piece in enumerate(body):
            self._out.put((piece, f"{tag}:start" if n == 0 else f"{tag}:end" if n == len(body) - 1 else None))
        while f"{tag}:end" not in self.marks and self.alive:
            time.sleep(0.05)
        return self.marks.get(f"{tag}:start", self.now()), self.marks.get(f"{tag}:end", self.now())

    def last_sound(self, since: float = 0.0) -> float | None:
        return next((t for t, pcm in reversed(self.frames) if t >= since and is_sound(pcm)), None)

    def quiet_now(self, for_seconds: float = 1.0) -> bool:
        last = self.last_sound()
        return last is None or self.now() - last > for_seconds


class LiveBridge:
    """formguide.voice over its one WebSocket (the route a native app uses): audio in and out as raw PCM16 mono
    24 kHz, the conversation's events beside it. On "heard" the runner posts the ordinary chat run in the same thread
    (the Visit), so every chat check reads that run. One session a scenario. Times are from this process's clock:
    the end of speech is the moment the clip's last piece was sent."""
    name = "live"
    HEAR_WAIT, ANSWER_WAIT = 20.0, 90.0    # seconds: for the words to be heard, for the answer to be over

    def __init__(self, base: str, code: str, max_usd: float):
        import uuid

        import httpx
        self.base, self.max_usd, self.spent, self.failed_starts = base.rstrip("/"), max_usd, 0.0, 0
        self.http = httpx.Client(base_url=self.base, timeout=180, headers={"X-Demo-Visitor": f"qa-{uuid.uuid4().hex[:8]}"})
        r = self.http.post("/voice/unlock", json={"code": code})
        if r.status_code != 200:
            raise SystemExit(f"{self.base}/voice/unlock answered {r.status_code}: is voice on at this host (VOICE_CODES), and is VOICE_BENCH_CODE one of its codes?")
        self.token = r.json()["pass"]

    def open(self, sc: Any) -> Session:
        import evals
        from harness_client import Visit
        from websockets.sync.client import connect
        if self.spent >= self.max_usd:
            raise StopSum(f"${self.spent:.2f} spent, the stop sum is ${self.max_usd:.2f}")
        visit = Visit(self.http, sc.page, answer=evals.RuleGuest(sc).choose, site=sc.site)
        visit.ticks = set()              # by voice no consent is ever ticked: a tick is a tap
        if sc.values and visit.form:
            visit.form.apply(sc.values)
        ws = connect(self.base.replace("http", "ws", 1) + f"/voice/stream?thread_id={visit.thread}",
                     additional_headers={"X-Voice-Pass": self.token}, max_size=None, open_timeout=30)
        first = json.loads(ws.recv(timeout=40))
        if first.get("type") != "started":
            self.failed_starts += 1
            self.spent += OPEN_SECONDS / 60 * 0.05   # not stated whether a failed start is billed: counted as billed
            ws.close()
            raise RuntimeError(f"the conversation did not start: {json.dumps(first)[:200]}")
        return Session(visit=visit, line=Line(ws))

    def say(self, s: Session, clip: dict, cut_in: bool, then_cut_in: bool = False) -> Turn:
        L: Line = s.line
        t = Turn(said=clip["text"], clip_seconds=float(clip.get("seconds") or 0), cut_in=cut_in)
        s.turns.append(t)
        if not cut_in:                   # a new line waits until the voice is silent; a cut-in speaks over it
            until = L.now() + 15
            while not L.quiet_now() and L.now() < until:
                time.sleep(0.1)
        seen = len(L.events)
        start, end = L.speak(pcm_of(Path(clip["file"]) if Path(clip["file"]).is_absolute() else CLIPS / clip["file"]), f"turn{len(s.turns)}")
        heard_at = answered = first_answer = None
        while L.alive:
            for at, ev in L.events[seen:]:
                seen += 1
                kind = ev.get("type")
                if kind == "heard" and str(ev.get("text") or "").strip():
                    t.heard = (t.heard + " " + ev["text"]).strip()
                    heard_at = heard_at if heard_at is not None else at
                    if not ev.get("answers"):    # the widget sends what was heard as an ordinary message of the same thread
                        try:
                            s.visit.say(ev["text"])
                        except Exception as e:  # noqa: BLE001
                            t.error = f"{type(e).__name__}: {e}"[:200]
                elif kind == "result":   # the answer reaches the voice sentence by sentence: the first is the useful one
                    answered = at
                    first_answer = first_answer if first_answer is not None else at
                    t.spoken = (t.spoken + " " + str(ev.get("text") or "")).strip()
                elif kind == "interrupted" and cut_in:
                    t.cancelled = True
                elif kind in ("error", "ended"):
                    t.error = t.error or f"{kind}: {json.dumps(ev)[:160]}"
            now = L.now()
            if t.error and "ended" in t.error:
                break
            if heard_at is None and now - end > self.HEAR_WAIT:
                t.error = t.error or f"nothing was heard in {self.HEAR_WAIT:.0f} s"
                break
            if answered is not None and then_cut_in and L.last_sound(answered) is not None:
                break                    # the answer has started to sound: the next line speaks over it
            if turn_over(L.last_sound(end), now, answered) or now - end > self.ANSWER_WAIT:
                break
            time.sleep(0.1)
        sounds = sound_times(L.frames, end)
        t.first_sound_s = sounds["first"]
        t.first_step_s = round(heard_at - end, 2) if heard_at is not None else None      # the words arrive: the run starts
        t.useful_s = round(first_answer - end, 2) if first_answer is not None else None   # the answer's first sentence is handed to the voice
        if cut_in:                       # from the cut-in's first piece to the voice falling silent
            loud = [at for at, pcm in L.frames if at >= start and is_sound(pcm)]
            gap = next((a for a, b in zip(loud, loud[1:] + [L.now() + 9]) if b - a > 0.5), None)
            t.silence_s = round(max(0.0, (gap if gap is not None else start) - start), 2)
            t.cancelled = bool(t.cancelled)
        return t

    def close(self, s: Session) -> None:
        L: Line = s.line
        try:
            L.ws.send(json.dumps({"type": "end"}))
        except Exception:  # noqa: BLE001
            pass
        until = time.monotonic() + 15
        ended = None
        while time.monotonic() < until and ended is None:
            ended = next((ev for _at, ev in L.events if ev.get("type") == "ended"), None)
            time.sleep(0.1)
        try:
            L.ws.close()
        except Exception:  # noqa: BLE001
            pass
        s.connected_s = float((ended or {}).get("seconds") or L.now())
        s.cost_usd = (ended or {}).get("cost_usd")
        self.spent += float(s.cost_usd if s.cost_usd is not None else s.connected_s / 60 * 0.05)
        s.visit.finish()


# ===================================================================== one scenario, the report


def clips_for(sc: Any, manifest: list[dict]) -> list[dict]:
    mine = sorted((c for c in manifest if c["scenario"] == sc.name), key=lambda c: c["turn"])
    if len(mine) != len(sc.scripted):
        raise SystemExit(f"{sc.name}: {len(mine)} clips for {len(sc.scripted)} lines: run scripts/voice_clips.py")
    return mine


def hard_outcome(sc: Any, visit: Any) -> str:
    """A hard-to-hear value, three ways (the Owner's decided behaviour: fill, light the field, read the value back):
    `exact` every expected field holds its value; `asked` no expected field holds anything and the assistant asked
    (acceptable, counted apart); `wrong` a field holds another value, or nothing was filled and nothing was asked."""
    import evals
    got = {n: next((f.config["state"].get(n) for f in visit.forms.values() if n in f.config.get("props", {})), None) for n in sc.fields}
    if all(evals._same(got[n], want) for n, want in sc.fields.items()):
        return "exact"
    asked = any("?" in text for _mid, text in visit.replies)
    return "asked" if asked and not any(str(v or "").strip() for v in got.values()) else "wrong"


def play(sc: Any, bridge: Any, manifest: list[dict]) -> dict:
    import evals
    s = bridge.open(sc)
    cut = "interruption" in sc.tags
    mine = clips_for(sc, manifest)
    try:
        for n, clip in enumerate(mine):
            bridge.say(s, clip, cut_in=cut and n > 0, then_cut_in=cut and n + 1 < len(mine))
    finally:                             # a session that was opened is always closed: an open one is billed
        bridge.close(s)
    checks = evals.checks(sc, s.visit)
    turns = []
    for t in s.turns:
        kept, of = entities_kept(t.said, t.heard)
        turns.append({**t.__dict__, "wer": wer(t.said, t.heard), "entities_kept": kept, "entities": of})
    tok = getattr(s.visit, "tokens", {}) or {}
    hard = hard_outcome(sc, s.visit) if "hard" in sc.tags else None
    return {"hard": hard, "name": sc.name, "group": sc.tags[1] if len(sc.tags) > 1 else "", "lang": sc.tags[2] if len(sc.tags) > 2 else "en",
            "turns": turns, "checks": checks, "ok": all(c.get("ok") for c in checks) and not any(t.error for t in s.turns),
            "connected_s": round(s.connected_s, 1), "cost_usd": s.cost_usd, "agent_tokens": dict(tok), "transcript": s.visit.transcript()}


def _q(xs: list[float], p: float) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    return round(xs[min(len(xs) - 1, int(p * len(xs)))], 2) if xs else None


def metrics(results: list[dict], usd_per_minute: float, agent_usd: float) -> dict:
    turns = [t for r in results for t in r["turns"]]
    plain = [t for t in turns if not t["cut_in"]]
    cuts = [t for t in turns if t["cut_in"]]
    seconds = sum(max(r["connected_s"], OPEN_SECONDS) for r in results)   # a failed start is counted as the minimum too
    voice_usd = round(seconds / 60 * usd_per_minute, 4)
    by: dict[str, list[bool]] = {}
    for r in results:
        by.setdefault(r["group"], []).append(r["ok"])
        by.setdefault("lang " + r["lang"], []).append(r["ok"])
    ents = (sum(t["entities_kept"] for t in turns), sum(t["entities"] for t in turns))
    return {
        "scenarios": len(results), "tasks_ok": sum(r["ok"] for r in results), "by": {k: [sum(v), len(v)] for k, v in sorted(by.items())},
        "wer_mean": round(statistics.mean(t["wer"] for t in turns), 3) if turns else None, "entities_kept": list(ents),
        "first_sound_p50": _q([t["first_sound_s"] for t in plain], 0.5), "first_sound_p90": _q([t["first_sound_s"] for t in plain], 0.9),
        "useful_p50": _q([t["useful_s"] for t in plain], 0.5), "useful_p90": _q([t["useful_s"] for t in plain], 0.9),
        "first_step_p50": _q([t["first_step_s"] for t in plain], 0.5),
        "hard": {k: sum(1 for r in results if r.get("hard") == k) for k in ("exact", "asked", "wrong")},
        "failed_starts": sum(1 for r in results if not r["turns"] or all(t["error"] for t in r["turns"])),
        "cut_ins": len(cuts), "cut_ins_cancelled": sum(1 for t in cuts if t["cancelled"]), "silence_p50": _q([t["silence_s"] for t in cuts], 0.5),
        "host_usd": round(sum(r["cost_usd"] for r in results if r.get("cost_usd") is not None), 4) if any(r.get("cost_usd") is not None for r in results) else None,
        "connected_minutes": round(seconds / 60, 2), "voice_usd": voice_usd, "agent_usd": round(agent_usd, 4),
        "usd_per_task": round((voice_usd + agent_usd) / max(1, len(results)), 4),
        "usd_per_minute": round((voice_usd + agent_usd) / max(0.01, seconds / 60), 4),
    }


def report_md(rep: dict) -> str:
    m = rep["metrics"]
    mock = rep["bridge"] == "mock"
    lines = [f"# Voice benchmark, {rep['at']}", "",
             f"Bridge `{rep['bridge']}`, set `{rep['set']}`, pass {rep['pass']}, {m['scenarios']} scenarios, commit `{rep['commit']}`.",
             ("**A mock run**: a scripted voice over an offline demo with a one-line model. It proves the runner, the clips, the "
              "scenarios and the checks. Its task results and its times say nothing about the product." if mock else
              "Speaker: recorded clips (the Mac's voices). A synthetic voice is cleaner than a person in a room: an upper bound."), "",
             "| Measure | Result |", "| --- | --- |",
             f"| tasks that pass their checks | {m['tasks_ok']} of {m['scenarios']} |",
             f"| heard: word error rate, mean | {m['wer_mean']} |",
             f"| heard: numbers and names kept | {m['entities_kept'][0]} of {m['entities_kept'][1]} |",
             f"| end of speech to the first sound, s | p50 {m['first_sound_p50']}, p90 {m['first_sound_p90']} |",
             f"| ... to the first step on screen, s | p50 {m['first_step_p50']} |",
             f"| ... to the first useful sentence, s | p50 {m['useful_p50']}, p90 {m['useful_p90']} |",
             f"| hard to hear: exact / asked to repeat, field empty / wrong value | {m['hard']['exact']} / {m['hard']['asked']} / {m['hard']['wrong']} |",
             f"| interruptions: the turn cancelled | {m['cut_ins_cancelled']} of {m['cut_ins']} (silence after p50 {m['silence_p50']} s) |",
             f"| billed minutes (a session is at least {OPEN_SECONDS} s) | {m['connected_minutes']} |",
             f"| sessions that did not start (counted as {OPEN_SECONDS} s each) | {m['failed_starts']} |",
             f"| dollars the host reports (voice seconds and the agent's turns) | {m['host_usd']} |",
             f"| dollars: voice / agent | {m['voice_usd']} / {m['agent_usd']} |",
             f"| dollars a task / a connected minute | {m['usd_per_task']} / {m['usd_per_minute']} |", "",
             "By group and language (tasks that pass): " + ", ".join(f"{k} {a}/{b}" for k, (a, b) in m["by"].items()), "", "## Failed", ""]
    for r in rep["results"]:
        if not r["ok"]:
            why = [c["check"] for c in r["checks"] if not c.get("ok")] + [t["error"] for t in r["turns"] if t["error"]]
            lines.append(f"- `{r['name']}`: {'; '.join(why)[:200]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="scenario names (default: the whole set)")
    ap.add_argument("--set", type=Path, default=SCENARIOS / "voice-v1.txt")
    ap.add_argument("--pass", dest="pass_no", type=int, default=1, help="which recording of the clips (voice_clips.py --pass)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--mock", action="store_true", help="the scripted voice over an offline demo: free")
    g.add_argument("--live", action="store_true", help="a real voice session (the owner's yes with a price, and --max-usd)")
    ap.add_argument("--garble", action="store_true", help="--mock: the voice mishears every digit, to see the hearing measures move")
    ap.add_argument("--max-usd", type=float, help="--live: stop opening sessions once this much is spent")
    ap.add_argument("--usd-per-minute", type=float, default=0.05, help="the voice's price per connected minute")
    ap.add_argument("--label", default="")
    ap.add_argument("--base", help="--live: the host with voice on, e.g. http://127.0.0.1:8097 (a stand of your own, never production)")
    a = ap.parse_args()
    if a.live and (a.max_usd is None or not a.base or not os.environ.get("VOICE_BENCH_CODE")):
        sys.exit("a live voice run needs --base, --max-usd and VOICE_BENCH_CODE in the environment (and the owner's yes with a price)")
    import evals
    mf = CLIPS / f"manifest-pass{a.pass_no}.json"
    if not mf.exists():
        sys.exit(f"no clips for pass {a.pass_no}: run scripts/voice_clips.py --pass {a.pass_no}")
    manifest = json.loads(mf.read_text())
    names = [n for n in a.set.read_text().split() if not a.names or n in a.names]
    scs = [evals.load_scenario(SCENARIOS / f"{n}.yaml") for n in names]
    if not scs:
        sys.exit("no scenarios match")
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        bridge = MockBridge(Path(tmp), a.garble) if a.mock else LiveBridge(a.base, os.environ["VOICE_BENCH_CODE"], a.max_usd)
        for sc in scs:
            try:
                r = play(sc, bridge, manifest)
            except StopSum as e:
                print(f"stopped: {e}; {len(scs) - len(results)} scenarios not run", flush=True)
                break
            except RuntimeError as e:   # a conversation that did not start: counted, the run goes on
                print(f"\u274c {sc.name:<30} {e}", flush=True)
                results.append({"name": sc.name, "group": sc.tags[1], "lang": sc.tags[2], "turns": [], "checks": [], "ok": False, "hard": None,
                                "connected_s": 0.0, "cost_usd": None, "agent_tokens": {}, "transcript": str(e)})
                continue
            results.append(r)
            t = r["turns"][-1]
            print(f"{'✅' if r['ok'] else '❌'} {sc.name:<30} {r['group']:<12} {r['lang']}  wer {max(x['wer'] for x in r['turns']):.2f}  "
                  f"sound {t['first_sound_s']}s useful {t['useful_s']}s  {r['connected_s']}s", flush=True)
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    rep = {"at": datetime.now().isoformat(timespec="seconds"), "bridge": bridge.name, "set": a.set.stem, "pass": a.pass_no, "commit": commit,
           "guest": "recorded clips", "metrics": metrics(results, a.usd_per_minute, 0.0), "results": results}
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"voice-{datetime.now():%Y%m%d-%H%M%S}-{bridge.name}{'-' + a.label if a.label else ''}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    out.with_suffix(".md").write_text(report_md(rep))
    print("\n" + report_md(rep))
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
