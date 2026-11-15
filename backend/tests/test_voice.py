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
        assert "card is on the screen" in said[0] and "went wrong" in said[1]
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
