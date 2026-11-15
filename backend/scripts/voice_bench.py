"""Voice benchmark: recorded clips speak, the voice mode answers, code checks the result. Design: evals/voice/README.md.

    uv run python scripts/voice_bench.py --mock                       # no session, no key, no money: the plumbing
    uv run python scripts/voice_bench.py --mock voice_fill_toyota     # one scenario
    uv run python scripts/voice_bench.py --live --max-usd 3.00        # a real session (needs the owner's yes and the bridge)

A scenario (evals/voice/*.yaml) is a chat scenario whose scripted lines are spoken: each line is a clip recorded once
by scripts/voice_clips.py with the Mac's own voice. Nothing here calls a model to play the person.

Two bridges:
  --mock   a scripted voice in this process: it "hears" the clip's own text, runs the ordinary Dushes turn on an
           offline demo (a one-line model), and "speaks" the first sentence of the reply. Times are those of this
           process, the voice's delays are fixed numbers. It proves the runner, the scenarios, the checks and the
           report; its task results say nothing about the product.
  --live   formguide.voice over its server-to-server transport. Not built yet: the runner states what it needs and
           stops. A paid voice run needs the owner's yes with a price (the CPO relays it) and a stop sum.

Measured per spoken line: what was heard against what was said (word error rate; numbers and names exactly), the
time from the end of speech to the first sound, to the first step on screen and to the first useful sentence; for an
interruption, the time to silence and whether the turn in progress was cancelled. Per scenario: the same code checks
as chat (fields, the page reached, stays_put_on, cards, never_says). Per run: connected seconds, dollars for the voice
and for the agent, per task and per minute.
"""
from __future__ import annotations

import argparse
import json
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
OPEN_SECONDS = 15          # billed when a session opens (gpt-live-1's list terms, read 2026-11-15)
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

    def say(self, s: Session, clip: dict, cut_in: bool) -> Turn:
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


class LiveBridge:
    """formguide.voice over its server-to-server transport. It needs, from the bridge: audio in and out as frames,
    the bridge's clock on every event (end of speech, delegation, run started, first text, result handed over, first
    audio out, response finished), the text heard and spoken, the Dushes turn's AG-UI events and thread, connected
    seconds and run_stats, a fixed voice and language, an event for an interruption, and a stop sum."""
    name = "live"

    def __init__(self, *_a: Any, **_k: Any):
        try:
            import formguide.voice  # noqa: F401
        except ImportError:
            raise SystemExit("formguide.voice is not in this checkout: the live voice run waits for the bridge. "
                             "Use --mock to run the scenarios against the scripted voice.") from None
        raise SystemExit("the live bridge's transport is not wired into this runner yet (it is written against the "
                         "bridge once it exists); and a paid voice run needs the owner's yes with a price.")


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
    for n, clip in enumerate(clips_for(sc, manifest)):
        bridge.say(s, clip, cut_in=cut and n > 0)
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
            "connected_s": round(s.connected_s, 1), "agent_tokens": dict(tok), "transcript": s.visit.transcript()}


def _q(xs: list[float], p: float) -> float | None:
    xs = sorted(x for x in xs if x is not None)
    return round(xs[min(len(xs) - 1, int(p * len(xs)))], 2) if xs else None


def metrics(results: list[dict], usd_per_minute: float, agent_usd: float) -> dict:
    turns = [t for r in results for t in r["turns"]]
    plain = [t for t in turns if not t["cut_in"]]
    cuts = [t for t in turns if t["cut_in"]]
    seconds = sum(r["connected_s"] for r in results) + OPEN_SECONDS * len(results)
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
        "cut_ins": len(cuts), "cut_ins_cancelled": sum(1 for t in cuts if t["cancelled"]), "silence_p50": _q([t["silence_s"] for t in cuts], 0.5),
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
             f"| connected minutes (with {OPEN_SECONDS} s a session at opening) | {m['connected_minutes']} |",
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
    a = ap.parse_args()
    if a.live and a.max_usd is None:
        sys.exit("a live voice run needs --max-usd (and the owner's yes with a price)")
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
        bridge = MockBridge(Path(tmp), a.garble) if a.mock else LiveBridge()
        for sc in scs:
            r = play(sc, bridge, manifest)
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
