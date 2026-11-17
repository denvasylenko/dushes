"""QA, fails first: words said over the voice that the provider never hands over (the owner's sessions, 2026-11-17).

In 3 of the 36 lines the owner began while the voice was speaking, the provider sent his words
(session.input_transcript.delta) but never a session.delegation.created for them: the line never reached the agent
and the voice went on with the old answer. The CPO's decision (2026-11-17): words that arrived while the voice was
speaking, with no hand-over from the provider within about 1.5 s after the person's last word, go to our agent as a
line, and its answer is spoken; never "sorry, what did you say?" (the words did arrive). A hand-over that comes late
for the same words must not make a second line or a second answer.

The first test is marked xfail(strict) until the behaviour is built: the mark comes off in the change that builds it.
The other two are guards that pass today and must keep passing.
"""
from __future__ import annotations

import asyncio

import pytest

from formguide import voice

from .test_voice import _talks

QUIET = 1.5          # the CPO's "about 1.5 s after the last word"
MARGIN = 1.0         # slack for the bridge's own timers


async def _speaking(live, talks, thread: str):
    """A conversation in which the agent's turn has ended and the voice is speaking its answer."""
    await talks.start("anna", "o", thread)
    events = talks.events("live_1")
    live.push(type="session.input_transcript.delta", delta="What does a car loan cost?")
    live.push(type="session.delegation.created", delegation={"id": "d1", "type": "delegation", "target": "client"})
    while (await asyncio.wait_for(events.__anext__(), 1))["type"] != "heard":
        pass
    for ev in ({"type": "RUN_STARTED"}, {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "A car loan starts from 18.9% a year."},
               {"type": "RUN_FINISHED"}):
        talks.seen(thread, ev)
    await asyncio.sleep(0.05)
    for word in (" A car", " loan", " starts", " from"):      # the voice says it
        live.push(type="session.output_transcript.delta", delta=word)
    await asyncio.sleep(0.05)
    return events


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


def _spoken(live) -> list[str]:
    return [m.get("content") or "" for m in live.sent if m.get("type") in ("session.commentary.append", "response.create", "session.say")]


@pytest.mark.xfail(strict=True, reason="QA fails-first: words with no hand-over are dropped today (CPO decision 2026-11-17)")
def test_words_said_over_the_voice_with_no_hand_over_reach_the_agent_and_are_answered():
    async def go():
        talks, live, _ = _talks()
        _drain = _Drain(await _speaking(live, talks, "cut-over"))
        live.push(type="session.input_transcript.delta", delta="No, the mortgage")   # over the voice; no delegation follows
        got = await _drain(QUIET + MARGIN)
        heard = [e for e in got if e["type"] == "heard"]
        assert [e["text"] for e in heard] == ["No, the mortgage"], f"the line never reached the agent: {[e['type'] for e in got]}"
        before = len(_spoken(live))
        for ev in ({"type": "RUN_STARTED"}, {"type": "TEXT_MESSAGE_CONTENT", "messageId": "n", "delta": "A mortgage starts from 16.5%."},
                   {"type": "RUN_FINISHED"}):
            talks.seen("cut-over", ev)
        await asyncio.sleep(0.1)
        new = _spoken(live)[before:]
        assert any("16.5%" in x for x in new), f"the answer was not given to the voice: {new}"
        assert not any(x == voice.UNHEARD for x in new)                  # the words arrived: no "say it again"
        await talks.end("live_1")
    asyncio.run(go())


def test_a_late_hand_over_for_the_same_words_makes_no_second_line_or_answer():
    """The guard for the change: passes today (the late hand-over is the only one), must still pass once the server
    hands the words over by itself (then the late hand-over must not add a second line or a second answer)."""
    async def go():
        talks, live, _ = _talks()
        _drain = _Drain(await _speaking(live, talks, "cut-late"))
        live.push(type="session.input_transcript.delta", delta="No, the mortgage")
        got = await _drain(QUIET + MARGIN)                      # the server hands it over itself
        live.push(type="session.delegation.created", delegation={"id": "d2", "type": "delegation", "target": "client"})
        got += await _drain(0.5)                                 # then the provider's own hand-over comes
        heard = [e for e in got if e["type"] == "heard"]
        assert [e["text"] for e in heard] == ["No, the mortgage"], f"lines handed over: {[e.get('text') for e in heard]}"
        before = len(_spoken(live))
        for ev in ({"type": "RUN_STARTED"}, {"type": "TEXT_MESSAGE_CONTENT", "messageId": "n", "delta": "A mortgage starts from 16.5%."},
                   {"type": "RUN_FINISHED"}):
            talks.seen("cut-late", ev)
        await asyncio.sleep(0.1)
        said = [x for x in _spoken(live)[before:] if "16.5%" in x]
        assert len(said) == 1, f"the answer was given to the voice {len(said)} times"
        await talks.end("live_1")
    asyncio.run(go())


def test_words_that_the_provider_hands_over_at_once_are_handed_over_once():
    """The guard: today's ordinary way (words, then the hand-over) stays one line, said once."""
    async def go():
        talks, live, _ = _talks()
        _drain = _Drain(await _speaking(live, talks, "cut-normal"))
        live.push(type="session.input_transcript.delta", delta="No, the mortgage")
        live.push(type="session.delegation.created", delegation={"id": "d2", "type": "delegation", "target": "client"})
        got = await _drain(QUIET + MARGIN)
        assert [e["text"] for e in got if e["type"] == "heard"] == ["No, the mortgage"]
        await talks.end("live_1")
    asyncio.run(go())
