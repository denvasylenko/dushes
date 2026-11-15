"""Voice mode, the part with no network: the codes (one per person), the pass, the limits (openspec/changes/voice-mode)."""
from __future__ import annotations

import pytest

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
