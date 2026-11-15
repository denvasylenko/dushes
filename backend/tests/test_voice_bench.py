"""The voice benchmark's own parts (scripts/voice_bench.py, voice_clips.py): the set, the clips' manifest, what is
measured about hearing, and a mock run. No session, no key, no audio is recorded here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import json  # noqa: E402

import evals  # noqa: E402
import voice_bench as vb  # noqa: E402
import voice_clips as vc  # noqa: E402

SET = vb.SCENARIOS / "voice-v1.txt"


def test_the_set_loads_and_covers_the_groups_and_three_languages():
    scs = [evals.load_scenario(vb.SCENARIOS / f"{n}.yaml") for n in SET.read_text().split()]
    assert len(scs) == 52 and all(s.tags[0] == "voice" and s.scripted for s in scs)
    groups = {g: sum(s.tags[1] == g for s in scs) for g in ("answer", "order", "offer_yes", "fill", "hard", "card", "fix", "interruption")}
    assert groups == {"answer": 10, "order": 5, "offer_yes": 6, "fill": 12, "hard": 5, "card": 4, "fix": 5, "interruption": 5}
    langs = {lang: sum(s.tags[2] == lang for s in scs) for lang in vc.LANGS}
    assert langs["en"] >= 20 and langs["ru"] >= 8 and langs["uk"] >= 6
    assert all(len(s.scripted) == 2 for s in scs if s.tags[1] == "interruption")     # the second clip is the cut-in
    consent = [s for s in scs if "accept_terms" in s.fields]
    assert consent and all(s.fields["accept_terms"] is False for s in consent)      # a spoken yes never ticks a consent


def test_every_spoken_line_has_one_clip_in_the_manifest():
    items = vc.manifest(SET, 1)
    assert len(items) == sum(len(evals.load_scenario(vb.SCENARIOS / f"{n}.yaml").scripted) for n in SET.read_text().split())
    assert {i["voice"] for i in items} == set(vc.VOICES.values()) and all(i["rate"] == vc.RATES[1] for i in items)
    assert vc.clip_id("en", "hello", 175) != vc.clip_id("en", "hello", 215) != vc.clip_id("ru", "hello", 215)   # a pass records its own clips
    faster = vc.manifest(SET, 2)
    assert [i["text"] for i in faster] == [i["text"] for i in items] and faster[0]["clip"] != items[0]["clip"]


def test_hearing_is_measured_by_words_and_by_the_things_that_matter():
    assert vb.wer("book me a haircut", "book me a haircut") == 0
    assert vb.wer("book me a haircut", "book me the haircut") == 0.25
    assert vb.wer("my age is thirty four", "") == 1
    assert vb.entities("the VIN of my Toyota is 555 and I am 34") == ["555", "34", "VIN", "Toyota", "I"]
    assert vb.entities_kept("Anna Kowalczyk, 34", "anna kovalchik 34") == (1, 2)       # the number kept, the surname lost


def test_a_mock_run_plays_a_scenario_end_to_end(tmp_path):
    sc = evals.load_scenario(vb.SCENARIOS / "voice_cut_in_order.yaml")
    manifest = [{**i, "seconds": 3.0} for i in vc.manifest(SET, 1)]
    r = vb.play(sc, vb.MockBridge(tmp_path), manifest)
    assert [t["said"] for t in r["turns"]] == list(sc.scripted.values()) and [t["heard"] for t in r["turns"]] == list(sc.scripted.values())
    assert [t["cut_in"] for t in r["turns"]] == [False, True] and r["turns"][1]["cancelled"] is True
    assert r["turns"][0]["first_sound_s"] is not None and r["connected_s"] > 6 and r["checks"]
    m = vb.metrics([r], 0.05, 0.0)
    assert m["cut_ins"] == 1 and m["cut_ins_cancelled"] == 1 and m["wer_mean"] == 0
    assert m["voice_usd"] == round(max(r["connected_s"], vb.OPEN_SECONDS) / 60 * 0.05, 4)   # 15 s is the least a session costs, not a charge on top
    short = vb.metrics([{**r, "connected_s": 4.0}], 0.05, 0.0)
    assert short["voice_usd"] == round(15 / 60 * 0.05, 4) and short["failed_starts"] == 0
    garbled = vb.play(evals.load_scenario(vb.SCENARIOS / "voice_card_refused_vin.yaml"), vb.MockBridge(tmp_path / "g", garble=False), manifest)
    assert garbled["turns"][0]["wer"] == 0


def test_a_live_run_stops_before_it_spends(monkeypatch):
    import pytest
    monkeypatch.delenv("VOICE_BENCH_CODE", raising=False)
    monkeypatch.setattr(sys, "argv", ["voice_bench.py", "--live", "--max-usd", "1"])
    with pytest.raises(SystemExit):      # no host and no code: nothing is opened
        vb.main()


def test_the_live_bridge_plays_a_clip_through_the_socket_and_reads_the_run(tmp_path):
    """The live path end to end without a provider and without money: the host's own /voice/stream with a scripted
    provider behind it (as tests/test_voice.py does), the offline demo for the chat run, a real socket between."""
    import asyncio
    import base64
    import socket
    import threading
    import time

    import uvicorn
    from formguide import voice

    class FakeLive:   # the provider's side: the test puts events in and reads what the bridge sent
        def __init__(self):
            self.inbox, self.sent, self.loop = asyncio.Queue(), [], asyncio.get_running_loop()

        def push(self, **ev):
            self.loop.call_soon_threadsafe(self.inbox.put_nowait, json.dumps(ev))

        async def send(self, raw):
            self.sent.append(json.loads(raw))

        async def close(self):
            self.inbox.put_nowait(None)

        def __aiter__(self):
            return self

        async def __anext__(self):
            raw = await self.inbox.get()
            if raw is None:
                raise StopAsyncIteration
            return raw

    lives = []

    async def opener(key, model, instructions):
        lives.append(FakeLive())
        return f"live_{len(lives)}", lives[-1]
    talks = voice.Talks(voice.VoiceConfig(codes={"qa": "qa-test-code-0001"}), title="the demo", key=lambda: "k")
    talks._stream_opener = opener
    app = evals.offline_client(tmp_path).app
    app.include_router(voice.create_voice_router(voice.watch(talks)), prefix="/voice")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    until = time.monotonic() + 20
    while not server.started and time.monotonic() < until:
        time.sleep(0.05)
    try:
        sc = evals.load_scenario(vb.SCENARIOS / "voice_ask_car_insurance.yaml")
        wav = tmp_path / "clip.wav"
        import wave
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(vb.SAMPLE_RATE)
            w.writeframes((2000).to_bytes(2, "little", signed=True) * (vb.SAMPLE_RATE // 2))   # half a second of sound
        manifest = [{"scenario": sc.name, "turn": 1, "text": sc.scripted[1], "file": str(wav), "seconds": 0.5}]
        bridge = vb.LiveBridge(f"http://127.0.0.1:{port}", "qa-test-code-0001", max_usd=1.0)

        def provider():   # hears the clip, hands the words over, then speaks the answer it is given
            while not lives or not any(m["type"] == "session.input_audio.append" for m in lives[0].sent):
                time.sleep(0.05)
            live = lives[0]
            time.sleep(0.8)
            live.push(type="session.input_transcript.delta", delta=sc.scripted[1])
            live.push(type="session.delegation.created", delegation={"id": "d1", "type": "delegation", "target": "client"})
            until = time.monotonic() + 20
            while time.monotonic() < until and not any("commentary" in m["type"] or "delegation" in m["type"] for m in live.sent):
                time.sleep(0.05)
            loud = base64.b64encode((3000).to_bytes(2, "little", signed=True) * 2400).decode()
            for _ in range(3):
                live.push(type="session.output_audio.delta", delta=loud)
        threading.Thread(target=provider, daemon=True).start()
        vb.END_OF_TURN, old = 0.5, vb.END_OF_TURN
        try:
            r = vb.play(sc, bridge, manifest)
        finally:
            vb.END_OF_TURN = old
    finally:
        server.should_exit = True
        if talks in voice.HOSTS:
            voice.HOSTS.remove(talks)
    t = r["turns"][0]
    assert t["heard"] == sc.scripted[1] and t["wer"] == 0 and not t["error"]
    assert t["first_step_s"] is not None and t["useful_s"] is not None and t["first_sound_s"] is not None
    assert "Offline answer" in r["transcript"]                 # the ordinary chat run of the same thread was read
    assert r["cost_usd"] is not None and r["connected_s"] > 0 and bridge.spent > 0


def test_sound_is_found_by_level_not_by_the_first_frame():
    quiet, loud = b"\x00" * vb.CHUNK, (2000).to_bytes(2, "little", signed=True) * (vb.CHUNK // 2)
    assert not vb.is_sound(quiet) and vb.is_sound(loud) and not vb.is_sound((300).to_bytes(2, "little", signed=True) * 100)
    # silence frames arrive at once; "one moment" at 2.2 s; a pause; the result spoken from 5.0 s
    frames = [(10.1, quiet), (10.2, quiet), (12.2, loud), (12.3, loud), (12.4, quiet), (15.0, loud), (15.1, loud)]
    assert vb.sound_times(frames, 10.0) == {"first": 2.2, "last": 5.1, "again": 5.0}
    assert vb.sound_times([(10.1, quiet)], 10.0) == {"first": None, "last": None, "again": None}
    assert vb.turn_over(last_sound=15.1, now=18.2, answered=14.0) and not vb.turn_over(15.1, 17.0, 14.0)
    assert not vb.turn_over(12.3, 16.0, 14.0)                      # only the "one moment" sounded: the result is still to come
    assert not vb.turn_over(15.1, 19.0, None)


def test_a_clip_goes_in_as_a_microphone_would_send_it(tmp_path):
    import wave
    p = tmp_path / "c.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(vb.SAMPLE_RATE); w.writeframes((1500).to_bytes(2, "little", signed=True) * vb.SAMPLE_RATE)   # one second
    pcm = vb.pcm_of(p)
    assert len(pcm) == vb.SAMPLE_RATE * 2
    parts = vb.pieces(pcm)
    assert len(parts) == 5 + 10 + 8 and all(len(x) == vb.CHUNK for x in parts)     # 100 ms pieces: half a second of silence, the clip, its tail
    assert not vb.is_sound(parts[0]) and vb.is_sound(parts[5]) and not vb.is_sound(parts[-1])


def test_the_english_set_is_the_english_scenarios_of_the_whole_set():
    en = (vb.SCENARIOS / "voice-v1-en.txt").read_text().split()
    scs = [evals.load_scenario(vb.SCENARIOS / f"{n}.yaml") for n in en]
    assert len(en) == 34 and all(s.tags[2] == "en" for s in scs) and set(en) <= set(SET.read_text().split())
    assert {s.tags[1] for s in scs} == {"answer", "order", "offer_yes", "fill", "hard", "card", "fix", "interruption"}   # every group is still there
    from collections import Counter
    assert min(Counter(s.tags[1] for s in scs).values()) >= 3   # no group is an anecdote


def test_a_hard_value_is_exact_or_asked_or_wrong():
    from types import SimpleNamespace as NS
    sc = NS(fields={"vin": "WVWZZZ1JZXW000001"})
    def visit(value, said):
        return NS(forms={"f": NS(config={"props": {"vin": {}}, "state": {"vin": value}})}, replies=[("m", said)])
    assert vb.hard_outcome(sc, visit("WVWZZZ1JZXW000001", "Done.")) == "exact"
    assert vb.hard_outcome(sc, visit("", "Could you say the VIN again?")) == "asked"       # acceptable, counted apart
    assert vb.hard_outcome(sc, visit("WVWZZZ1JZXW000007", "Is that right?")) == "wrong"    # a wrong value in the field is a failure, asked or not
    assert vb.hard_outcome(sc, visit("", "Done.")) == "wrong"                              # nothing filled and nothing asked


def test_a_card_that_asks_for_a_tap_fails_a_voice_fill_and_a_quiet_one_passes():
    from types import SimpleNamespace as NS
    sc = evals.load_scenario(vb.SCENARIOS / "voice_fill_term_bare_number.yaml")

    class Empty(NS):
        def __getattr__(self, name):
            return []

    def run(card):
        got = {c["check"]: c["ok"] for c in evals.checks(sc, Empty(log=[], forms={}, form=None, cards=[card]))}
        return got["no field-change card without quiet"]
    row = {"type": "set_fields", "changes": [{"label": "Loan term", "display": "36 months"}]}
    assert run(row) is False and run({**row, "quiet": True}) is True
