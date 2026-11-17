"""QA, fails first: speaking over the voice (the owner's sessions, 2026-11-17).

The record of his talking sessions: 36 of his 132 lines began while the voice was speaking; the voice went on for
4 to 14 more words in 15 of them, and 3 lines were lost (the provider sent his words, session.input_transcript.delta,
but never a session.delegation.created for them). In every one the agent's turn had already ended, so the server's
own stop of a running turn never applied. The CPO said yes to two fixes, in order; Owner TL wrote what each must do.

1. Cut-in (VOICE_CUT_IN=1, a trial): his words while the voice's last word is under 1.2 s old -> ONE
   session.instructions.append (delegation_id None, our own sentence, never his words) and `interrupted` (by: words)
   to the client; once per stretch; not for one word the voice itself said lately, not for an echo of 4+ words.
2. Words with no hand-over (its own switch, not built): his words arrived, no hand-over came, N seconds passed after
   his last word (N = voice.UNHANDED_WAIT, 1.5 s; the tests shorten it) -> the server emits `heard` with the text,
   and the run's answer is given to the voice with no delegation id. Never "I did not catch that". Guards: a late
   hand-over gets an empty thinking note and no second `heard`; a new word resets the clock; an echo and a filler-only
   stretch are never handed over.

The tests of what is not built yet are xfail(strict): the mark comes off in the change that builds it. The phrases are
synthetic, shaped like the three lost lines (nine words, a bare yes, four words); none is the owner's.
"""
from __future__ import annotations

import asyncio

import pytest

from formguide import voice

from .test_voice import _talks

MARGIN = 0.5
NOT_BUILT = pytest.mark.xfail(strict=True, reason="QA fails-first: not built on this commit (CPO's yes, 2026-11-17)")
LOST = [["Wait,", " that is", " not what", " I", " asked", " you", " about", " just", " now"], ["yes"], [" No,", " the", " other", " one"]]


class _Drain:
    """Reads the conversation's events in the background (a timeout on the stream itself would close it)."""

    def __init__(self, events):
        self.got: list[dict] = []
        self.seen = 0

        async def read():
            async for e in events:
                self.got.append(e)
        self.task = asyncio.ensure_future(read())

    async def __call__(self, seconds: float) -> list[dict]:
        await asyncio.sleep(seconds)
        new, self.seen = self.got[self.seen:], len(self.got)
        return new


async def _speaking(live, talks, thread: str) -> _Drain:
    """A conversation in which the agent's turn has ended and the voice is speaking its answer."""
    await talks.start("anna", "o", thread)
    events = talks.events("live_1")
    live.push(type="session.input_transcript.delta", delta="What does a car loan cost?")
    live.push(type="session.delegation.created", delegation={"id": "d1", "type": "delegation", "target": "client"})
    while (await asyncio.wait_for(events.__anext__(), 1))["type"] != "heard":
        pass
    _answer(talks, thread, "A car loan starts from 18.9% a year.")
    await asyncio.sleep(0.05)
    drain = _Drain(events)
    for word in (" A car", " loan", " starts", " from"):      # the voice says it
        live.push(type="session.output_transcript.delta", delta=word)
    await drain(0.05)
    return drain


def _answer(talks, thread: str, text: str) -> None:
    for ev in ({"type": "RUN_STARTED"}, {"type": "TEXT_MESSAGE_CONTENT", "messageId": "n", "delta": text}, {"type": "RUN_FINISHED"}):
        talks.seen(thread, ev)


def _given(live, text: str) -> list[dict]:
    """What the voice was given that holds `text` (any message the bridge sends with a content)."""
    return [m for m in live.sent if text in str(m.get("content") or "")]


# ---------------------------------------------------------------- 1. cut-in (VOICE_CUT_IN=1)

def _cuts(live) -> list[dict]:
    return [m for m in live.sent if m.get("type") == "session.instructions.append"]


@pytest.mark.parametrize("words", LOST)
def test_his_words_over_the_voice_cut_it_once(monkeypatch, words):
    monkeypatch.setenv("VOICE_CUT_IN", "1")

    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "cut-in")
        for w in words:
            live.push(type="session.input_transcript.delta", delta=w)
        got = await drain(0.2)
        cuts = [e for e in got if e["type"] == "interrupted"]
        assert len(cuts) == 1 and cuts[0].get("by") == "words", [e["type"] for e in got]
        sent = _cuts(live)
        assert len(sent) == 1 and sent[0].get("delegation_id") is None
        assert not any(w.strip(" ,").lower() in sent[0]["content"].lower() for w in words if len(w.strip(" ,")) > 3)   # never his words
        await talks.end("live_1")
    asyncio.run(go())


def test_no_cut_when_the_switch_is_off_or_the_voice_is_quiet_or_it_is_an_echo(monkeypatch):
    """Guards: they pass today and must keep passing once the cut-in is built."""
    async def run(switch, wait_before, words):
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "cut-guard")
        await drain(wait_before)
        for w in words:
            live.push(type="session.input_transcript.delta", delta=w)
        got = await drain(0.2)
        await talks.end("live_1")
        return [e for e in got if e["type"] == "interrupted"], _cuts(live)
    monkeypatch.delenv("VOICE_CUT_IN", raising=False)
    assert asyncio.run(run(False, 0, ["No,", " the other one"])) == ([], [])              # the switch is off
    monkeypatch.setenv("VOICE_CUT_IN", "1")
    assert asyncio.run(run(True, 1.5, ["No,", " the other one"])) == ([], [])             # the voice stopped 1.5 s ago
    assert asyncio.run(run(True, 0, ["from"])) == ([], [])                                 # one word the voice just said
    assert asyncio.run(run(True, 0, ["A car loan starts from"])) == ([], [])               # the voice's own words back, at once


def test_the_voices_own_words_coming_back_word_by_word_do_not_cut_it(monkeypatch):
    """Guard: an echo arrives as the transcript does, a word or two a delta. Its first two words are the voice's
    own, so they are not his: no cut (Owner TL: "not for 4+ words that repeat the voice")."""
    monkeypatch.setenv("VOICE_CUT_IN", "1")

    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "cut-echo")
        for w in ("A car", " loan", " starts", " from"):
            live.push(type="session.input_transcript.delta", delta=w)
        got = await drain(0.2)
        await talks.end("live_1")
        return [e for e in got if e["type"] == "interrupted"], _cuts(live)
    assert asyncio.run(go()) == ([], [])


# ---------------------------------------------------------------- 2. words with no hand-over

@pytest.fixture
def quick(monkeypatch):
    monkeypatch.setattr(voice, "UNHANDED_WAIT", 0.3, raising=False)
    return voice.UNHANDED_WAIT


@NOT_BUILT
@pytest.mark.parametrize("words", LOST)
def test_words_with_no_hand_over_reach_the_agent_and_are_answered(quick, words):
    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "unhanded")
        for w in words:
            live.push(type="session.input_transcript.delta", delta=w)
        got = await drain(quick + MARGIN)
        heard = [e for e in got if e["type"] == "heard"]
        assert [e["text"] for e in heard] == ["".join(words).strip()], f"the line never reached the agent: {[e['type'] for e in got]}"
        _answer(talks, "unhanded", "A mortgage starts from 16.5%.")
        await drain(0.1)
        given = _given(live, "16.5%")
        assert len(given) == 1 and given[0].get("delegation_id") is None, given
        assert not _given(live, voice.UNHEARD)                       # the words were caught: never "say it again"
        await talks.end("live_1")
    asyncio.run(go())


@NOT_BUILT
def test_a_late_hand_over_after_the_server_took_the_line_gets_an_empty_note_and_no_second_line(quick):
    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "unhanded-late")
        live.push(type="session.input_transcript.delta", delta="No, the other one")
        got = await drain(quick + MARGIN)                           # the server took it
        live.push(type="session.delegation.created", delegation={"id": "d2", "type": "delegation", "target": "client"})
        got += await drain(0.3)                                     # then the provider's own hand-over comes
        assert [e["text"] for e in got if e["type"] == "heard"] == ["No, the other one"]
        notes = [m for m in live.sent if m.get("type") == "session.thinking.append" and m.get("delegation_id") == "d2"]
        assert notes and all(m.get("content") == "" for m in notes), notes
        _answer(talks, "unhanded-late", "A mortgage starts from 16.5%.")
        await drain(0.1)
        assert len(_given(live, "16.5%")) == 1                       # answered once
        await talks.end("live_1")
    asyncio.run(go())


@NOT_BUILT
def test_a_new_word_resets_the_clock(quick):
    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "unhanded-slow")
        live.push(type="session.input_transcript.delta", delta="No, the")
        got = await drain(quick * 0.6)
        live.push(type="session.input_transcript.delta", delta=" other one")
        got += await drain(quick * 0.6)
        assert not [e for e in got if e["type"] == "heard"]          # still speaking: nothing yet
        got += await drain(quick + MARGIN)
        assert [e["text"] for e in got if e["type"] == "heard"] == ["No, the other one"]
        await talks.end("live_1")
    asyncio.run(go())


@pytest.mark.parametrize("words", [["A car", " loan", " starts", " from"], ["uh"], ["[sigh]"], [" uh", " [sigh]", " mm"]])
def test_an_echo_or_a_filler_is_never_handed_over(quick, words):
    """Guards: they pass today (nothing is handed over without the provider) and must keep passing once it is built."""
    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "unhanded-noise")
        for w in words:
            live.push(type="session.input_transcript.delta", delta=w)
        got = await drain(quick + MARGIN)
        assert not [e for e in got if e["type"] == "heard"], [e.get("text") for e in got if e["type"] == "heard"]
        await talks.end("live_1")
    asyncio.run(go())


def test_words_that_the_provider_hands_over_at_once_are_handed_over_once(quick):
    """The guard for the ordinary way (words, then the hand-over): one line, said once."""
    async def go():
        talks, live, _ = _talks()
        drain = await _speaking(live, talks, "handed")
        live.push(type="session.input_transcript.delta", delta="No, the other one")
        live.push(type="session.delegation.created", delegation={"id": "d2", "type": "delegation", "target": "client"})
        got = await drain(quick + MARGIN)
        assert [e["text"] for e in got if e["type"] == "heard"] == ["No, the other one"]
        _answer(talks, "handed", "A mortgage starts from 16.5%.")
        await drain(0.1)
        assert len(_given(live, "16.5%")) == 1
        await talks.end("live_1")
    asyncio.run(go())
