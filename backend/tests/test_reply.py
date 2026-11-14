"""A reply to a quote reaches both agents and comes back on restore."""
from __future__ import annotations

import asyncio
from pathlib import Path

from formguide.agui import run_kwargs
from formguide.reply import clean, quoted, resolve
from formguide.site import Dushes, SiteMap

from .conftest import say
from .test_agent import BARBER, collect, start

SITE = Path(__file__).resolve().parents[1] / "demo" / "site.yaml"


def body(**fwd):
    return {"threadId": "t", "runId": "r", "messages": [{"role": "user", "content": "why so high?"}],
            "state": {}, "tools": [], "context": [], "forwardedProps": fwd}


def test_the_field_is_read_and_cleaned():
    kw = run_kwargs(body(reply_to={"message_id": "msg_1", "quote": "  The monthly payment is\n 32 945  "}))
    assert kw["reply_to"] == [{"message_id": "msg_1", "quote": "The monthly payment is 32 945"}]   # old client: one object
    assert "reply_to" not in run_kwargs(body())                                   # an old client
    assert clean({"quote": "x" * 400})[0]["quote"].endswith("\u2026") and len(clean({"quote": "x" * 400})[0]["quote"]) == 300
    assert clean({"quote": "   "}) is None and quoted("hi", None) == "hi"


def test_a_reply_to_the_whole_answer():
    assert clean({"message_id": "m1", "whole": True}) == [{"whole": True, "message_id": "m1"}]
    entries = [{"kind": "assistant", "message_id": "m1", "text": "Saturday 10:00 to 16:00."}]
    got = quoted("why?", resolve([{"whole": True, "message_id": "m1"}], entries))
    assert got.startswith("[The user replies to your whole earlier answer: \u00abSaturday 10:00 to 16:00.\u00bb]")
    assert "(your previous answer)" in quoted("why?", resolve([{"whole": True, "message_id": "gone"}], entries))


def test_several_quotes_with_notes_in_order():
    rt = clean([{"message_id": "m1", "quote": "18.9% a year", "note": "  too high  "},
                {"message_id": "m2", "quote": "60 months"}, {"quote": ""}, "junk"])
    assert rt == [{"message_id": "m1", "quote": "18.9% a year", "note": "too high"},
                  {"message_id": "m2", "quote": "60 months"}]
    got = quoted("", rt).split("\n")
    assert got == ["[The user replies to this part of your earlier answer: \u00ab18.9% a year\u00bb] Their comment: \u00abtoo high\u00bb",
                   "[The user replies to this part of your earlier answer: \u00ab60 months\u00bb]"]
    assert len(clean([{"quote": "q"}] * 20)) == 10 and len(clean({"quote": "q", "note": "n" * 2000})[0]["note"]) == 1000


def test_the_restore_says_whether_the_server_transcribes(guide):
    from formguide.transcribe import Transcriber, TranscriptionConfig
    guide.transcriber = None
    assert guide.thread("tr0")["transcription"] is False
    guide.transcriber = Transcriber(TranscriptionConfig())
    assert guide.thread("tr0")["transcription"] is True
    assert Dushes(guide, SiteMap.load(SITE)).thread("tr0")["transcription"] is True


def test_the_form_agent_reads_the_quote_and_keeps_it(guide, model):
    model.script = [say("It follows the 18.9% rate.")]
    rt = {"message_id": "msg_1", "quote": "The monthly payment is 32 945"}
    collect(guide, "rq1", message="why so high?", state=start(guide, BARBER), reply_to=rt)
    last = model.calls[-1][-1].content
    text = last if isinstance(last, str) else " ".join(b.get("text", "") for b in last if isinstance(b, dict))
    assert "replies to this part of your earlier answer: \u00abThe monthly payment is 32 945\u00bb" in text
    user = next(e for e in guide.thread("rq1")["transcript"] if e["kind"] == "user")
    assert user["text"] == "why so high?" and user["reply_to"] == [rt]             # the bubble keeps the plain text
    assert next(m for m in guide.thread_messages("rq1") if m["role"] == "user")["reply_to"] == [rt]


def test_dushes_reads_the_quote_and_restore_returns_it(guide, model):
    site = Dushes(guide, SiteMap.load(SITE))
    model.script = [say("Saturday hours are shorter.")]
    rt = {"message_id": "msg_9", "quote": "Open 10:00 to 16:00 on Saturday"}

    async def go():
        return [e async for e in site.run("rq2", message="why shorter?", state={"page": {"path": "/"}}, reply_to=rt)]
    asyncio.run(go())
    assert "\u00abOpen 10:00 to 16:00 on Saturday\u00bb" in str(model.calls[-1][-1].content)
    user = site.thread("rq2")["messages"][0]
    assert user == {"id": user["id"], "role": "user", "content": "why shorter?", "reply_to": [rt]}


def test_restore_keeps_the_live_message_id(guide, model):
    site = Dushes(guide, SiteMap.load(SITE))
    model.script = [say("Saturday 10:00 to 16:00.")]

    async def go():
        return [e async for e in site.run("rq3", message="when are you open?", state={"page": {"path": "/"}})]
    ev = asyncio.run(go())
    live = next(e["messageId"] for e in ev if e["type"] == "TEXT_MESSAGE_START")
    assert site.thread("rq3")["messages"][-1]["id"] == live                   # a quote from before a reload still points at it
