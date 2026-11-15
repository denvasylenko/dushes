"""Record the voice benchmark's speaker: one clip per spoken line, made with the Mac's own voices. Free and offline.

    uv run python scripts/voice_clips.py                 # every line of evals/voice/voice-v1.txt
    uv run python scripts/voice_clips.py --pass 2        # the second pass: a faster rate
    uv run python scripts/voice_clips.py --list          # the manifest only, no audio

The speaker of the voice benchmark is never a model (the API pays for the voice session and the agent only): each
line of a scenario is spoken once by `say` and kept as a WAV file (PCM 16-bit, mono, 24 kHz). The text of a clip is
known exactly, so what the voice model heard can be compared with it. Clips go to scripts/runs/voice-clips/ (not
into the repository: they are rebuilt from the scenarios); the manifest lists each clip's text, language, voice,
rate and length in seconds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
SCENARIOS = HERE / "evals" / "voice"
OUT = Path(__file__).parent / "runs" / "voice-clips"
VOICES = {"en": "Samantha", "ru": "Milena", "uk": "Lesya"}     # the Mac's own voices, one a language
RATES = {1: 175, 2: 215}                                         # words a minute: an ordinary pace, then a hurried one
SAMPLE_RATE = 24000
LANGS = tuple(VOICES)


def lines(set_file: Path) -> list[dict]:
    """Every spoken line of the set: {scenario, turn, lang, text}."""
    import evals
    out = []
    for name in set_file.read_text().split():
        sc = evals.load_scenario(SCENARIOS / f"{name}.yaml")
        lang = next((t for t in sc.tags if t in LANGS), "en")
        out += [{"scenario": sc.name, "turn": n, "lang": lang, "text": text} for n, text in sorted(sc.scripted.items())]
    return out


def clip_id(lang: str, text: str, rate: int) -> str:
    return f"{lang}-{hashlib.sha1(f'{lang}|{rate}|{text}'.encode()).hexdigest()[:12]}"


def record(text: str, voice: str, rate: int, path: Path) -> float:
    """Speak `text` into a WAV file; the clip's length in seconds."""
    aiff = path.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", str(aiff), text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SAMPLE_RATE}", "-c", "1", str(aiff), str(path)], check=True)
    aiff.unlink()
    with wave.open(str(path)) as w:
        return round(w.getnframes() / w.getframerate(), 2)


def manifest(set_file: Path, pass_no: int) -> list[dict]:
    rate, seen, out = RATES[pass_no], set(), []
    for ln in lines(set_file):
        cid = clip_id(ln["lang"], ln["text"], rate)
        out.append({**ln, "clip": cid, "voice": VOICES[ln["lang"]], "rate": rate, "file": f"{cid}.wav", "new": cid not in seen})
        seen.add(cid)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", type=Path, default=SCENARIOS / "voice-v1.txt")
    ap.add_argument("--pass", dest="pass_no", type=int, choices=sorted(RATES), default=1)
    ap.add_argument("--list", action="store_true", help="print the manifest and record nothing")
    a = ap.parse_args()
    items = manifest(a.set, a.pass_no)
    if a.list:
        print(json.dumps(items, ensure_ascii=True, indent=1))
        return 0
    if not shutil.which("say") or not shutil.which("afconvert"):
        sys.exit("recording needs macOS (say, afconvert)")
    have = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    missing = [v for v in VOICES.values() if v not in have]
    if missing:
        sys.exit(f"voices not installed: {', '.join(missing)} (System Settings > Accessibility > Spoken Content > System Voice)")
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0.0
    for it in items:
        p = OUT / it["file"]
        if it["new"] or not p.exists():
            it["seconds"] = record(it["text"], it["voice"], it["rate"], p)
        else:
            with wave.open(str(p)) as w:
                it["seconds"] = round(w.getnframes() / w.getframerate(), 2)
        total += it["seconds"]
    (OUT / f"manifest-pass{a.pass_no}.json").write_text(json.dumps(items, ensure_ascii=True, indent=1))
    by = {lang: round(sum(i["seconds"] for i in items if i["lang"] == lang), 1) for lang in LANGS}
    print(f"{len(items)} clips, {total:.0f} s of speech {by}; manifest: {OUT / f'manifest-pass{a.pass_no}.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
