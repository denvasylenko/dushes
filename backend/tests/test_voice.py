"""Voice mode, the part with no network: the codes (one per person), the pass, the limits (openspec/changes/voice-mode)."""
from __future__ import annotations

import pytest

from .conftest import say as say_

from formguide.voice import TRIES_PER_DAY, Gate, Meter, VoiceConfig, parse_codes


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


CODES = {"anna": "anna-code-0001", "ben": "ben-code-00002"}


def test_without_a_code_there_is_no_voice_mode():
    assert not VoiceConfig().enabled and not VoiceConfig.from_env({}).enabled
    cfg = VoiceConfig.from_env({"VOICE_CODES": "anna=anna-code-0001, ben=ben-code-00002", "VOICE_DAY_USD": "5",
                                "VOICE_MAX_SECONDS": "120"})
    assert cfg.enabled and cfg.codes == CODES and cfg.day_usd == 5 and cfg.max_seconds == 120 and cfg.model == "gpt-live-1"


def test_a_weak_or_ambiguous_list_of_codes_is_refused():
    for bad in ("anna", "anna=short", "an na=anna-code-0001", "anna=anna-code-0001,anna=other-code-01",
                "anna=same-code-0001,ben=same-code-0001"):
        with pytest.raises(ValueError):
            parse_codes(bad)
    assert parse_codes("") == {} and parse_codes(" , ") == {}


def test_a_code_gives_a_pass_that_names_its_person():
    clock = Clock()
    gate = Gate(VoiceConfig(codes=CODES), clock)
    assert gate.unlock("nope-nope-nope") is None
    who, token = gate.unlock("  ben-code-00002 ")
    assert who == "ben" and gate.person(token) == "ben"
    assert gate.person(None) is None and gate.person("ben.9999999999.forged") is None
    assert gate.person(token.replace("ben.", "anna.")) is None          # a pass cannot be renamed
    assert Gate(VoiceConfig(codes=CODES), clock).person(token) is None   # another host's secret does not accept it
    clock.t += 13 * 3600
    assert gate.person(token) is None                                    # it expires


def test_a_withdrawn_code_ends_its_passes_and_leaves_the_others():
    cfg = VoiceConfig(codes=dict(CODES), secret="s" * 32)
    gate = Gate(cfg, Clock())
    _, anna = gate.unlock("anna-code-0001")
    _, ben = gate.unlock("ben-code-00002")
    del cfg.codes["anna"]
    assert gate.person(anna) is None and gate.person(ben) == "ben"


def test_wrong_tries_are_limited_per_address_and_day():
    clock = Clock()
    gate = Gate(VoiceConfig(codes=CODES), clock)
    for _ in range(TRIES_PER_DAY):
        assert gate.unlock("wrong-wrong-wrong", "1.2.3.4") is None
    assert gate.unlock("anna-code-0001", "1.2.3.4") is None              # even the right code, from that address
    assert gate.unlock("anna-code-0001", "5.6.7.8") is not None          # another address is not punished
    clock.t += 24 * 3600
    assert gate.unlock("anna-code-0001", "1.2.3.4") is not None          # the next day


def test_one_conversation_at_a_time_and_its_three_ends():
    clock = Clock()
    meter = Meter(VoiceConfig(codes=CODES, max_seconds=300, max_usd=0.75, silence_seconds=30), clock)
    assert meter.refusal("anna") is None
    meter.start("t1", "anna")
    assert meter.refusal("ben") == "busy"
    clock.t += 20
    meter.report("t1", seconds=20, heard=True)
    assert meter.over("t1") is None
    clock.t += 31
    assert meter.over("t1") == "silence"                                 # nobody spoke for half a minute
    meter.report("t1", heard=True)
    meter.report("t1", agent_usd=0.72)                                   # the agent's own turns count too
    assert meter.over("t1") == "money"
    assert round(meter.end("t1", seconds=52), 4) == round(52 / 60 * 0.05 + 0.72, 4)
    meter.start("t2", "ben")
    clock.t += 300
    assert meter.over("t2") == "time"                                    # five minutes, by the clock when no report came


def test_the_days_budget_counts_reported_seconds_and_resets():
    clock = Clock()
    meter = Meter(VoiceConfig(codes=CODES, day_usd=0.10, person_day_usd=0.06, max_seconds=10_000, max_usd=100,
                              silence_seconds=10_000), clock)
    meter.start("t1", "anna")
    clock.t += 60
    meter.report("t1", seconds=30)        # a late report never makes the spend smaller than the clock says
    assert round(meter.spent(), 3) == 0.05 and round(meter.spent("anna"), 3) == 0.05
    meter.report("t1", seconds=72)        # a snapshot, not an addition
    meter.report("t1", seconds=72)
    assert round(meter.end("t1", seconds=72), 3) == 0.06
    assert meter.refusal("anna") == "person_day" and meter.refusal("ben") is None
    meter.start("t2", "ben")
    clock.t += 60
    assert meter.over("t2") == "day" and meter.end("t2") > 0             # the stand's budget ends an open conversation
    assert meter.refusal("ben") == "day"
    clock.t += 24 * 3600
    assert meter.refusal("anna") is None and meter.spent() == 0          # a new day


# ---------------------------------------------------------------- the conversation, with a scripted voice provider

import asyncio  # noqa: E402
import json  # noqa: E402

from formguide import voice  # noqa: E402


class FakeLive:
    """The provider's attached WebSocket: the test puts events in, and reads what the bridge sent."""

    def __init__(self):
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.sent: list[dict] = []
        self.closed = False

    def push(self, **ev):
        self.inbox.put_nowait(json.dumps(ev))

    async def send(self, raw):
        self.sent.append(json.loads(raw))

    async def close(self):
        self.closed = True
        self.inbox.put_nowait(None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        raw = await self.inbox.get()
        if raw is None:
            raise StopAsyncIteration
        return raw


def _talks(**limits):
    live = FakeLive()
    seen_open = {}

    async def opener(key, model, sdp, instructions):
        seen_open.update(key=key, model=model, sdp=sdp, instructions=instructions)
        return "live_1", "ANSWER-SDP", live
    cfg = voice.VoiceConfig(codes=CODES, **limits)
    return voice.Talks(cfg, title="Aster Bank", key=lambda: "k", opener=opener), live, seen_open


def test_what_is_heard_becomes_a_run_and_the_answer_is_spoken():
    async def go():
        talks, live, opened = _talks()
        got = await talks.start("anna", "OFFER-SDP", "thread-1")
        assert got["talk"] == "live_1" and got["sdp"] == "ANSWER-SDP" and got["limits"]["seconds"] == 300
        assert opened["model"] == "gpt-live-1" and "Aster Bank" in opened["instructions"] and opened["sdp"] == "OFFER-SDP"
        live.push(type="session.input_transcript.delta", delta="What does a car ")
        live.push(type="session.input_transcript.delta", delta="loan cost?")
        live.push(type="session.delegation.created", delegation={"id": "item_1", "type": "delegation", "target": "client"})
        events = talks.events("live_1")
        growing = [await asyncio.wait_for(events.__anext__(), 1) for _ in range(2)]
        assert [(e["type"], e["delta"]) for e in growing] == [("hearing", "What does a car "), ("hearing", "loan cost?")]
        heard = await asyncio.wait_for(events.__anext__(), 1)
        assert heard["type"] == "heard" and heard["text"] == "What does a car loan cost?" and "t_ms" in heard
        # the client sends the ordinary run with that text; its events pass the run route, which reports them here
        for ev in ({"type": "RUN_STARTED"}, {"type": "TEXT_MESSAGE_CONTENT", "messageId": "lead", "delta": "Let me look. "},
                   {"type": "CUSTOM", "name": "text_retract", "value": {"messageId": "lead"}},
                   {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "A car loan starts **from 18.9%** a year "},
                   {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "([Loans](/loans))."},
                   {"type": "CUSTOM", "name": "run_stats", "value": {"cost_usd": 0.002}}, {"type": "RUN_FINISHED"}):
            voice.watch(talks)
            voice.seen("thread-1", ev)
        voice.seen("another-thread", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "x", "delta": "not ours"})
        result = await asyncio.wait_for(events.__anext__(), 1)
        assert result == {"type": "result", "text": "A car loan starts from 18.9% a year (Loans).", "t_ms": result["t_ms"]}
        await asyncio.sleep(0)
        said = [m for m in live.sent if m["type"] == "session.commentary.append"]
        assert len(said) == 1 and said[0]["delegation_id"] == "item_1" and said[0]["content"] == result["text"]
        assert talks.meter.open["live_1"].agent_usd == 0.002                     # the agent's turn counts in the limit
        live.push(type="session.usage.updated", usage={"seconds": 42})
        live.push(type="session.closed", reason="close_requested", usage={"seconds": 60})
        ended = await asyncio.wait_for(events.__anext__(), 1)
        assert ended["type"] == "ended" and ended["reason"] == "close_requested" and ended["cost_usd"] == 0.052
        assert not talks.meter.open and round(talks.meter.spent("anna"), 3) == 0.052
        voice.HOSTS.clear()
    asyncio.run(go())


def test_a_run_that_ends_with_a_card_or_an_error_still_gives_the_voice_something_to_say():
    async def go():
        talks, live, _ = _talks()
        await talks.start("anna", "o", "t1")
        talks.seen("t1", {"type": "CUSTOM", "name": "on_interrupt", "value": "{}"})
        talks.seen("t1", {"type": "RUN_FINISHED"})
        talks.seen("t1", {"type": "RUN_ERROR", "message": "x"})
        await asyncio.sleep(0.01)
        said = [m["content"] for m in live.sent if m["type"] == "session.commentary.append"]
        assert "yes or no" in said[0] and "confirm it there" not in said[0] and "went wrong" in said[1]
        await talks.end("live_1")
        assert live.closed and {"type": "session.close"} in live.sent
    asyncio.run(go())


def test_a_second_conversation_is_refused_and_a_limit_ends_one():
    async def go():
        talks, live, _ = _talks(max_seconds=0)        # the time limit is reached at once
        await talks.start("anna", "o", "t1")
        with pytest.raises(voice.Refused) as e:
            await talks.start("ben", "o", "t2")
        assert str(e.value) == "busy"
        events = talks.events("live_1")
        ended = await asyncio.wait_for(events.__anext__(), 3)
        assert ended["type"] == "ended" and ended["reason"] == "time" and live.closed
    asyncio.run(go())


def test_the_routes_need_a_pass_and_never_take_it_from_the_address():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    talks, _live, _ = _talks()
    app = FastAPI()
    app.include_router(voice.create_voice_router(talks), prefix="/voice")
    with TestClient(app) as c:
        assert c.post("/voice/unlock", json={"code": "wrong-wrong-wrong"}).status_code == 403
        got = c.post("/voice/unlock", json={"code": "anna-code-0001"}).json()
        assert got["person"] == "anna"
        assert c.post("/voice/session", json={"sdp": "o", "thread_id": "t"}).status_code == 403          # no pass
        assert c.get("/voice/events", params={"talk": "x", "pass": got["pass"]}).status_code == 403    # not in the address
        r = c.post("/voice/session", json={"sdp": "o", "thread_id": "t"}, headers={"X-Voice-Pass": got["pass"]})
        assert r.status_code == 200 and r.json()["sdp"] == "ANSWER-SDP"
        ben = c.post("/voice/unlock", json={"code": "ben-code-00002"}).json()["pass"]
        busy = c.post("/voice/session", json={"sdp": "o", "thread_id": "t2"}, headers={"X-Voice-Pass": ben})
        assert busy.status_code == 429 and busy.json()["detail"] == {"reason": "busy"}
        assert c.get("/voice/events", params={"talk": "live_1"}, headers={"X-Voice-Pass": ben}).status_code == 404   # not his
        ended = c.post("/voice/end", json={"talk": "live_1"}, headers={"X-Voice-Pass": got["pass"]})
        assert ended.status_code == 200 and ended.json()["cost_usd"] >= 0          # the person sees what it cost


def test_a_host_without_codes_has_no_voice_routes():
    from fastapi.testclient import TestClient

    from docs_ai import host
    assert not host.VOICE.config.enabled
    with TestClient(host.app) as c:
        assert c.post("/voice/unlock", json={"code": "anything-at-all"}).status_code in (404, 405)
        assert c.get("/voice-lab/").status_code == 404


def test_an_answer_that_will_be_spoken_is_short_and_has_no_chips(guide, model, tmp_path):
    """From the owner's first voice session (2026-11-15): every answer waited for the suggestion chips nobody sees
    in voice, and came as a paragraph with a list. In a voice conversation the model is told its answer is heard,
    and no chips are made. The record keeps the person's words alone."""
    from .test_agent import collect, start
    from .test_questions import LOAN

    async def go():
        talks, live, _ = _talks()
        talks.log_dir = tmp_path
        voice.watch(talks)
        await talks.start("anna", "o", "spoken-thread")
        return talks, live
    talks, _live = asyncio.run(go())
    try:
        assert voice.active("spoken-thread") and not voice.active("typed-thread")
        model.script = [say_("The department code goes on the Applicant tab.")]
        ev = collect(guide, "spoken-thread", message="where is the department code", state=start(guide, LOAN))
        told = " ".join(str(getattr(m, "content", "")) for m in model.calls[-1])
        assert "will HEAR your answer" in told and "where is the department code" in told
        user = next(e for e in guide.thread("spoken-thread")["transcript"] if e["kind"] == "user")
        assert user["text"] == "where is the department code"                        # the note is the model's alone
        assert not [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "suggestions"]
        model.script = [say_("It is on the Applicant tab.")]
        collect(guide, "typed-thread", message="where is the department code", state=start(guide, LOAN))
        assert "will HEAR your answer" not in " ".join(str(getattr(m, "content", "")) for m in model.calls[-1])
        logged = [json.loads(line) for f in tmp_path.glob("*.jsonl") for line in f.read_text().splitlines()]
        assert logged[0]["type"] == "started" and logged[0]["person"] == "anna" and logged[0]["thread"] == "spoken-thread"
    finally:
        voice.HOSTS.clear()


def test_numbers_as_people_say_them():
    n = voice.said_numbers
    assert n("ninety-two eighty five") == ["92", "85"] and n("four four three four") == ["4", "4", "3", "4"]
    assert n("five hundred thousand rubles") == ["500000"] and n("one hundred and twenty five") == ["125"]
    assert n("building ninety-three, apartment sixty three") == ["93", "63"]
    assert n("issued on 2015-06-10") == ["2015", "06", "10"] and n("no numbers here") == []


def test_only_what_the_person_said_into_an_empty_field_is_quiet():
    row = lambda name, value, display=None, **more: {"name": name, "value": value, "display": display or str(value),  # noqa: E731
                                                     "previous": None, **more}
    said = "So, it's like, four four three four. And I born in Lugansk, Ukraine"
    assert voice.quiet({"changes": [row("passport_series", "4434"), row("birth_place", "Lugansk, Ukraine")]}, said)
    loan = [row("loan_amount", 500000, "500 000"), row("loan_type", {"id": "consumer", "name": "Consumer loan"}, "Consumer loan")]
    assert voice.quiet({"changes": loan}, "yes so I see consumer loan five hundred thousand rubles")
    # the owner's session: he said Luhansk and "some Piterburg" for the region; the agent chose the city itself
    city = [row("reg_city", {"id": "spb", "name": "Saint Petersburg"}, "Saint Petersburg")]
    assert not voice.quiet({"changes": city}, "okay pick some Piterburg")
    assert not voice.quiet({"changes": [row("first_name", "Denis") | {"previous": "Den"}]}, "my name is Denis")   # replaces
    assert not voice.quiet({"changes": [row("agree", True, "Yes", consent=True)]}, "yes")                          # a consent
    assert not voice.quiet({"changes": [row("birth_date", "1992-07-01", "1 July 1992")]}, "first July ninety-two")  # worked out
    # the owner's second session: "let's try 36" for a term whose label is "36 months" came as a card
    term = [row("loan_term", {"id": 36, "name": "36 months"}, "36 months")]
    assert voice.quiet({"changes": term}, "Like, okay, let's try 36") and not voice.quiet({"changes": term}, "let's try 48")
    # the CPO's decision from that session: "for my car" clearly names the option "Car loan" of the field "Loan
    # type" and is filled quietly; "New car" for the purpose is a guess (new or used was not said) and is not
    said_car = "so what is left, this is for my car"
    car = row("loan_type", {"id": "auto", "name": "Car loan"}, "Car loan", label="Loan type")
    new = row("loan_purpose", {"id": "new_car", "name": "New car"}, "New car", label="Loan purpose")
    assert voice.quiet({"changes": [car]}, said_car)
    assert not voice.quiet({"changes": [new]}, said_car) and not voice.quiet({"changes": [car, new]}, said_car)
    assert voice.quiet({"changes": [new]}, "it is for a new car") and not voice.quiet({"changes": [car]}, "a mortgage please")
    assert not voice.quiet({"changes": [row("first_name", "Denis")]}, "") and not voice.quiet({"changes": []}, "x")
    assert not voice.quiet({"type": "ask", "changes": [row("first_name", "Denis")]}, "Denis")


def test_a_quiet_card_is_marked_and_not_announced(guide, model):
    from .test_agent import collect, start
    from .test_questions import LOAN

    async def open_talk():
        talks, live, _ = _talks()
        voice.watch(talks)
        await talks.start("anna", "o", "quiet-thread")
        return talks, live
    talks, live = asyncio.run(open_talk())
    try:
        model.script = [say_("", ("p1", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]}))]
        ev = collect(guide, "quiet-thread", message="my first name is Anna", state=start(guide, LOAN))
        raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
        card = json.loads(raw) if isinstance(raw, str) else raw
        assert card.get("quiet") is True and card["changes"][0]["name"] == "first_name"

        async def bridge():
            for e in ev:
                talks.seen("quiet-thread", e)
            got = await asyncio.wait_for(talks.events("live_1").__anext__(), 1)
            await asyncio.sleep(0.01)
            return got
        got = asyncio.run(bridge())
        assert got["type"] == "quiet" and got["card_id"] == card["card_id"]
        assert not [m for m in live.sent if m["type"] == "session.commentary.append"]   # nothing said about a card

        model.script = [say_("", ("p2", "propose_changes", {"changes": [{"name": "last_name", "value": "Smith"}]}))]
        ev = collect(guide, "typed-thread-2", message="my last name is Smith", state=start(guide, LOAN))
        raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
        assert "quiet" not in (json.loads(raw) if isinstance(raw, str) else raw)        # chat is untouched
    finally:
        voice.HOSTS.clear()


def test_the_voices_own_words_coming_back_are_not_a_request(monkeypatch):
    """From the owner's session on laptop speakers: the assistant's spoken question came back through his microphone
    and was sent as his message. Four words or more that repeat what the voice just said are dropped at the bridge,
    for every client; a short answer is never dropped."""
    said = [(100.0, "Sure. "), (100.5, "Choose the date and "), (101.0, "time of the booking, please.")]
    assert voice.is_echo("choose the date and time of the booking", said, now=103.0)
    assert not voice.is_echo("choose the date and time of the booking", said, now=130.0)      # long after: his own words
    assert not voice.is_echo("the booking", said, now=103.0)                                  # a short answer always goes
    assert not voice.is_echo("choose another date and time please", said, now=103.0)

    async def go():
        talks, live, _ = _talks()
        await talks.start("anna", "o", "echo-thread")
        events = talks.events("live_1")
        live.push(type="session.output_transcript.delta", delta="What is the loan for, a new car or a used one?")
        live.push(type="session.input_transcript.delta", delta="What is the loan for, a new car or a used one")
        live.push(type="session.delegation.created", delegation={"id": "item_e", "type": "delegation", "target": "client"})
        live.push(type="session.input_transcript.delta", delta="A used one")
        live.push(type="session.delegation.created", delegation={"id": "item_r", "type": "delegation", "target": "client"})
        seen = []
        while not seen or seen[-1]["type"] != "heard":
            seen.append(await asyncio.wait_for(events.__anext__(), 1))
        assert [e["type"] for e in seen if e["type"] in ("echo", "heard")] == ["echo", "heard"]
        assert seen[-1]["text"] == "A used one"
        assert any(m["type"] == "session.thinking.append" and m["content"] == "" for m in live.sent)   # no "let me check"
        await talks.end("live_1")
    asyncio.run(go())

    monkeypatch.setenv("VOICE_AS_IF", "voice-")
    assert voice.active("voice-test-1") and not voice.active("chat-test-1")


def test_audio_through_the_server_for_a_client_without_webrtc():
    """The CTO's D-20 and QA's runner: a native app (or a test runner) may not hold the provider's key and has no
    WebRTC, so its audio passes through this server on one socket, with the conversation's events beside it."""
    import base64

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    talks, _unused, _ = _talks()
    live = FakeLive()

    async def stream_opener(key, model, instructions):
        return "live_s", live
    talks._stream_opener = stream_opener
    app = FastAPI()
    app.include_router(voice.create_voice_router(talks), prefix="/voice")
    with TestClient(app) as c:
        with c.websocket_connect("/voice/stream?thread_id=t-ios") as ws:          # no pass
            assert ws.receive_json() == {"type": "refused", "reason": "pass"}
        token = c.post("/voice/unlock", json={"code": "anna-code-0001"}).json()["pass"]
        with c.websocket_connect("/voice/stream?thread_id=t-ios", headers={"X-Voice-Pass": token}) as ws:
            started = ws.receive_json()
            assert started["type"] == "started" and started["talk"] == "live_s"
            assert started["audio"] == {"format": "pcm16", "rate": 24000, "channels": 1}
            ws.send_bytes(b"\x01\x00\x02\x00\x03")                                 # an odd byte is not half a sample
            live.push(type="session.input_transcript.delta", delta="My middle name is Marie")
            live.push(type="session.delegation.created", delegation={"id": "d1", "type": "delegation", "target": "client"})
            live.push(type="session.output_audio.delta", delta=base64.b64encode(b"\x10\x00\x20\x00").decode())
            got, sound = [], b""
            while len(got) < 2 or not sound:
                message = ws.receive()
                if message.get("bytes"):
                    sound += message["bytes"]
                elif message.get("text"):
                    got.append(json.loads(message["text"]))
            assert [e["type"] for e in got] == ["hearing", "heard"] and got[1]["text"] == "My middle name is Marie"
            assert sound == b"\x10\x00\x20\x00"                                    # the voice's audio, as raw PCM
            sent = [m for m in live.sent if m["type"] == "session.input_audio.append"]
            assert sent and base64.b64decode(sent[0]["audio"]) == b"\x01\x00\x02\x00"
            ws.send_text(json.dumps({"type": "end"}))
            while True:
                message = ws.receive()
                if message.get("type") == "websocket.close":
                    break
                if message.get("text") and json.loads(message["text"])["type"] == "ended":
                    break
    assert not talks.meter.open and live.closed and {"type": "session.close"} in live.sent


def test_a_spoken_yes_or_no_answers_a_waiting_card():
    """The owner's session (2026-11-15) and the CPO's decision: a turn ended on a card that waited for a tap, the
    voice said "confirm it on the screen" and the conversation stalled; "I said yes" ticked nothing. The voice now
    asks the card's own question, a plain yes or no is the answer to that card, and silence under it ends nothing."""
    yes = voice.yes_or_no
    assert yes("Yes") is True and yes("yes please") is True and yes("I said yes") is True and yes("ok, do it") is True
    da, net = "".join(map(chr, (0x434, 0x430))), "".join(map(chr, (0x43D, 0x435, 0x442)))   # a Russian yes and no
    assert yes(da) is True and yes(net) is False and yes("No thanks") is False
    assert yes("yes, but make it 48 months") is None and yes("yes no") is None and yes("car loan") is None and yes("") is None
    card = {"type": "set_fields", "card_id": "c9", "changes": [{"name": "loan_type", "label": "Loan type", "display": "Car loan"},
                                                               {"name": "loan_purpose", "label": "Purpose", "display": "New car"}]}
    said = voice.asks(card)
    assert "Loan type: Car loan" in said and "Purpose: New car" in said and "yes or no" in said
    assert "Which city" in voice.asks({"type": "ask", "question": "Which city is it?", "options": [{"id": "a", "label": "Kolpino"}]})

    async def go():
        clock = Clock()
        talks, live, _ = _talks(silence_seconds=30)
        talks.meter.now = clock
        await talks.start("anna", "o", "card-thread")
        events = talks.events("live_1")
        for ev in ({"type": "RUN_STARTED"}, {"type": "CUSTOM", "name": "on_interrupt", "value": json.dumps(card)},
                   {"type": "RUN_FINISHED"}):
            talks.seen("card-thread", ev)
        result = await asyncio.wait_for(events.__anext__(), 1)
        assert result["type"] == "result" and "Loan type: Car loan" in result["text"] and "yes or no" in result["text"]
        assert "screen" not in result["text"]             # the voice asks; it never points at the screen
        clock.t += 120                                     # two minutes of thinking it over: not a silence
        await asyncio.sleep(1.2)
        assert "live_1" in talks.meter.open
        live.push(type="session.input_transcript.delta", delta="Yes, please")
        live.push(type="session.delegation.created", delegation={"id": "d2", "type": "delegation", "target": "client"})
        seen = []
        while not seen or seen[-1]["type"] != "heard":
            seen.append(await asyncio.wait_for(events.__anext__(), 1))
        assert seen[-1]["answers"] == {"card_id": "c9", "type": "set_fields", "accepted": True}
        talks.seen("card-thread", {"type": "RUN_STARTED"})   # the client answered the card: nothing waits now
        live.push(type="session.input_transcript.delta", delta="yes")
        live.push(type="session.delegation.created", delegation={"id": "d3", "type": "delegation", "target": "client"})
        seen = []
        while not seen or seen[-1]["type"] != "heard":
            seen.append(await asyncio.wait_for(events.__anext__(), 1))
        assert "answers" not in seen[-1]                     # a yes with no card waiting is an ordinary message
        await talks.end("live_1")
    asyncio.run(go())


def test_a_host_names_the_person_and_keeps_the_money_itself():
    """The cabinet's three hooks for hosting voice (2026-11-15): the host names the person of a request its own
    way, the day's spend comes from the host's ledger and each conversation's cost is reported to it, and the
    one-conversation rule is per person."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    ledger: dict[str, float] = {"c7": 5.0}
    costs = []
    cfg = voice.VoiceConfig(day_usd=50, person_day_usd=5, at_once=10, at_once_person=1)
    lives = []

    async def stream_opener(key, model, instructions):
        lives.append(FakeLive())
        return f"live_{len(lives)}", lives[-1]
    talks = voice.Talks(cfg, key=lambda: "k",
                        person_of=lambda headers: {"Bearer a": "c1", "Bearer b": "c2", "Bearer z": "c7"}.get(headers.get("authorization")),
                        spent_today=lambda person: ledger.get(person, 0.0) if person else sum(ledger.values()),
                        on_cost=lambda person, usd, seconds: costs.append((person, round(usd, 4), round(seconds))))
    talks._stream_opener = stream_opener
    app = FastAPI()
    app.include_router(voice.create_voice_router(talks), prefix="/voice")
    with TestClient(app) as c:
        with c.websocket_connect("/voice/stream?thread_id=t0") as ws:                       # nobody the host knows
            assert ws.receive_json() == {"type": "refused", "reason": "pass"}
        with c.websocket_connect("/voice/stream?thread_id=t7", headers={"Authorization": "Bearer z"}) as ws:
            assert ws.receive_json() == {"type": "refused", "reason": "person_day"}        # the host's ledger says so
        with c.websocket_connect("/voice/stream?thread_id=t1", headers={"Authorization": "Bearer a"}) as one:
            assert one.receive_json()["type"] == "started"
            with c.websocket_connect("/voice/stream?thread_id=t1b", headers={"Authorization": "Bearer a"}) as again:
                assert again.receive_json() == {"type": "refused", "reason": "busy"}       # one a person
            with c.websocket_connect("/voice/stream?thread_id=t2", headers={"Authorization": "Bearer b"}) as two:
                assert two.receive_json()["type"] == "started"                              # another person may talk
                two.send_text(json.dumps({"type": "end"}))
            one.send_text(json.dumps({"type": "end"}))
    assert sorted(p for p, _, _ in costs) == ["c1", "c2"] and all(usd >= 0 for _, usd, _ in costs)

    gate = voice.Gate(voice.VoiceConfig())                 # or the host issues the pass itself, with no code
    assert gate.person(gate.issue("c42")) == "c42"
    with pytest.raises(ValueError):
        gate.issue("not a plain word")


def test_speaking_over_an_answer_stops_the_turn_and_its_voice():
    """Task 2.6: the person speaks while the agent's turn is still running. The turn is stopped on the server, the
    client is told, and nothing of that turn is spoken; what they said now is the request."""
    async def go():
        talks, live, _ = _talks()
        stopped = []
        talks._stop = stopped.append
        await talks.start("anna", "o", "cut-thread")
        events = talks.events("live_1")
        talks.seen("cut-thread", {"type": "RUN_STARTED"})
        talks.seen("cut-thread", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "The car loan starts from "})
        live.push(type="session.input_transcript.delta", delta="Wait, not the car loan, the mortgage")
        live.push(type="session.delegation.created", delegation={"id": "d9", "type": "delegation", "target": "client"})
        seen = []
        while not seen or seen[-1]["type"] != "heard":
            seen.append(await asyncio.wait_for(events.__anext__(), 1))
        assert [e["type"] for e in seen if e["type"] in ("interrupted", "heard")] == ["interrupted", "heard"]
        assert stopped == ["cut-thread"]
        # the stopped turn may still send its last events: none of it reaches the voice
        talks.seen("cut-thread", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "18.9% a year."})
        talks.seen("cut-thread", {"type": "RUN_FINISHED"})
        await asyncio.sleep(0.01)
        assert not [m for m in live.sent if m["type"] == "session.commentary.append"]
        # the new request's own turn is spoken as usual
        for ev in ({"type": "RUN_STARTED"}, {"type": "TEXT_MESSAGE_CONTENT", "messageId": "n", "delta": "A mortgage starts from 16.5%."},
                   {"type": "RUN_FINISHED"}):
            talks.seen("cut-thread", ev)
        await asyncio.sleep(0.01)
        said = [m["content"] for m in live.sent if m["type"] == "session.commentary.append"]
        assert said == ["A mortgage starts from 16.5%."]
        # speaking when no turn is running interrupts nothing
        live.push(type="session.input_transcript.delta", delta="And for how many years")
        live.push(type="session.delegation.created", delegation={"id": "d10", "type": "delegation", "target": "client"})
        seen = []
        while not seen or seen[-1]["type"] != "heard":
            seen.append(await asyncio.wait_for(events.__anext__(), 1))
        assert "interrupted" not in [e["type"] for e in seen] and stopped == ["cut-thread"]
        await talks.end("live_1")
    asyncio.run(go())


def test_shortened_numbers_and_the_owners_ways_to_say_yes():
    """The owner's session of 2026-11-15, 22:59 UTC: "50k" for 50000 came as a card, and "Yeah, but say that Yes"
    was not taken as a yes."""
    n = voice.said_numbers
    assert n("I know it's like 50k") == ["50000"] and n("1.5 million for four years") == ["1500000", "4"]
    assert n("one and a half million") == ["1500000"] and n("half a million") == ["500000"] and n("2,5 mln") == ["2500000"]
    poltora = "".join(map(chr, (0x43F, 0x43E, 0x43B, 0x442, 0x43E, 0x440, 0x430)))           # "one and a half"
    million = "".join(map(chr, (0x43C, 0x438, 0x43B, 0x43B, 0x438, 0x43E, 0x43D, 0x430)))    # "of a million"
    assert n(f"{poltora} {million}") == ["1500000"]
    amount = {"name": "loan_amount", "label": "Loan amount", "value": 50000, "display": "50 000", "previous": None}
    assert voice.quiet({"changes": [amount]}, "50k") and not voice.quiet({"changes": [amount]}, "about sixty")
    yes = voice.yes_or_no
    assert yes("Yeah, but say that Yes") is True and yes("yes, all good") is True and yes("set it") is True
    assert yes("yes but make it 48 months") is None and yes("yes but 48") is None


def test_a_card_the_person_said_yes_to_is_not_asked_twice(guide, model, monkeypatch):
    """The same session: "Shall I fill in Loan amount 50000?" - "Yes" - the same question again, three times. His
    tab sent the yes as a message, which closes the card; the agent proposed the same value again and it waited
    again. A card with the same values as the one just confirmed is applied, whatever client sent the yes."""
    from .test_agent import collect, start
    from .test_questions import LOAN
    monkeypatch.setenv("VOICE_AS_IF", "voice-")
    state = start(guide, LOAN)

    def card(ev):
        raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
        return json.loads(raw) if isinstance(raw, str) else raw

    propose = ("p", "propose_changes", {"changes": [{"name": "birth_date", "value": "1990-07-01"}]})
    model.script = [say_("", propose)]
    first = card(collect(guide, "voice-again", message="I was born on the first of July, nineteen ninety", state=state))
    assert "quiet" not in first                                   # a date the agent assembled: it asks
    model.script = [say_("", ("p2", *propose[1:]))]
    again = card(collect(guide, "voice-again", message="Yes. Yes", state=state))
    assert again.get("quiet") is True and again["card_id"] != first["card_id"]

    model.script = [say_("", propose)]                             # the same in an ordinary chat thread: it waits
    collect(guide, "chat-again", message="I was born on the first of July, nineteen ninety", state=state)
    model.script = [say_("", ("p3", *propose[1:]))]
    assert "quiet" not in card(collect(guide, "chat-again", message="Yes", state=state))

    model.script = [say_("", propose)]                             # a yes to nothing, then another value: it waits
    collect(guide, "voice-other", message="I was born on the first of July, nineteen ninety", state=state)
    model.script = [say_("", ("p4", "propose_changes", {"changes": [{"name": "birth_date", "value": "1991-07-01"}]}))]
    assert "quiet" not in card(collect(guide, "voice-other", message="Yes", state=state))


def test_the_first_sentence_is_spoken_while_the_rest_is_still_written():
    """The cabinet's first voice run (2026-11-16): the voice said it was checking, then waited 6.8 s for the whole
    answer. A whole sentence goes to the voice once the next one has begun; a lead before a step (one sentence,
    then a tool) waits, and a lead that is taken back and written again is not said twice."""
    assert voice.ready("It costs 18.9% a year. The term") == 0                  # the next sentence has barely begun
    assert voice.ready("It costs 18.9% a year. The term is up to seven years") == 23
    assert voice.ready("Let me look. ") == 0                                    # a lead: nothing after it yet

    async def go():
        talks, live, _ = _talks()
        await talks.start("anna", "o", "t1")
        live.push(type="session.input_transcript.delta", delta="What does a car loan cost?")
        live.push(type="session.delegation.created", delegation={"id": "item_1"})
        events = talks.events("live_1")
        assert [(await asyncio.wait_for(events.__anext__(), 1))["type"] for _ in range(2)] == ["hearing", "heard"]
        said = lambda: [(m["delegation_id"], m["content"]) for m in live.sent if m["type"] == "session.commentary.append"]  # noqa: E731
        talks.seen("t1", {"type": "RUN_STARTED"})
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "lead", "delta": "Let me look. "})
        talks.seen("t1", {"type": "CUSTOM", "name": "text_retract", "value": {"messageId": "lead"}})
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "A car loan starts **from 18.9%** a year. "})
        await asyncio.sleep(0.01)
        assert said() == []                                                     # one sentence so far: it may be a lead
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "The term is up to seven years, "})
        await asyncio.sleep(0.01)
        assert said() == [("item_1", "A car loan starts from 18.9% a year.")]   # said while the rest is written
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "with no fee."})
        talks.seen("t1", {"type": "RUN_FINISHED"})
        await asyncio.sleep(0.01)
        assert said()[1:] == [("item_1", "The term is up to seven years, with no fee.")]   # the rest, the same request
        results = [await asyncio.wait_for(events.__anext__(), 1) for _ in range(2)]
        assert [r["type"] for r in results] == ["result", "result"]
        # a lead that was said, then taken back and written again: once
        live.push(type="session.input_transcript.delta", delta="And the fee?")
        live.push(type="session.delegation.created", delegation={"id": "item_2"})
        await asyncio.sleep(0.01)
        talks.seen("t1", {"type": "RUN_STARTED"})
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "a", "delta": "There is no fee at all. Let me check the early repayment"})
        talks.seen("t1", {"type": "CUSTOM", "name": "text_retract", "value": {"messageId": "a"}})
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "b", "delta": "There is no fee at all. Early repayment is free."})
        talks.seen("t1", {"type": "RUN_FINISHED"})
        await asyncio.sleep(0.01)
        assert said()[2:] == [("item_2", "There is no fee at all."), ("item_2", "Early repayment is free.")]
        # everything said on the way: nothing is added at the end, and no "Done"
        talks.seen("t1", {"type": "RUN_STARTED"})
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "c", "delta": "It is on the Applicant tab. "})
        talks.seen("t1", {"type": "TEXT_MESSAGE_CONTENT", "messageId": "c", "delta": "                    "})
        talks.seen("t1", {"type": "RUN_FINISHED"})
        await asyncio.sleep(0.01)
        assert [c for _, c in said()[4:]] == ["It is on the Applicant tab."]
        voice.HOSTS.clear()
    asyncio.run(go())


def test_a_number_in_words_with_k():
    """QA's list from the owner's voice log (2026-11-16): "two hundred k" is 200000 said aloud."""
    assert voice.said_numbers("two hundred k") == ["200000"] and voice.said_numbers("ok, fifty k then") == ["50000"]
    assert voice.said_numbers("plan k") == []
