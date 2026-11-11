"""Display transcript and durable history (chat-history capability)."""
from __future__ import annotations

import json

import asyncio

from langchain_core.messages import ToolMessage

from demo.mock_forms import FORMS
from formguide import FileTranscriptStore, FormGuide, GuideConfig, Models, sqlite_checkpointer

from .conftest import ScriptedChatModel, say
from .test_agent import collect, start

LOAN = FORMS["loan_application"]


def kinds(guide, thread):
    return [(e["kind"], e.get("status")) for e in guide.thread(thread)["transcript"]]


def test_transcript_records_turns_and_card_status(guide, model):
    model.script = [
        say("", ("t1", "focus_field", {"name": "loan_type", "hint": "Here"}),
            ("t2", "propose_changes", {"changes": [{"name": "loan_type", "value": "auto"}]})),
        say("Done."),
        say("", ("t3", "propose_changes", {"changes": [{"name": "loan_amount", "value": "900000"}]})),
        say("Where would you like to go?"),
    ]
    state = start(guide, LOAN)
    ev = collect(guide, "h1", message="I want a car loan", state=state)
    card_id = next(json.loads(e["value"])["card_id"] for e in ev if e.get("name") == "on_interrupt")
    t = guide.thread("h1")
    assert t["pending_card"]["id"] == card_id
    assert kinds(guide, "h1") == [("user", None), ("tool", None), ("tool", None), ("card", "pending")]

    new_cfg = LOAN.compute({**state["config"]["state"], "loan_type": {"id": "auto", "name": "Car loan"}})
    collect(guide, "h1", resume={"accepted": True, "config": new_cfg})
    assert kinds(guide, "h1")[-2:] == [("card", "accepted"), ("assistant", None)]

    collect(guide, "h1", message="900k please", state={**state, "config": new_cfg})
    collect(guide, "h1", message="actually, wait", state={**state, "config": new_cfg})   # card ignored
    statuses = [s for k, s in kinds(guide, "h1") if k == "card"]
    assert statuses == ["accepted", "dismissed"] and guide.thread("h1")["pending_card"] is None
    texts = [e.get("text") for e in guide.thread("h1")["transcript"] if e["kind"] in ("user", "assistant")]
    assert texts == ["I want a car loan", "Done.", "900k please", "actually, wait", "Where would you like to go?"]


def test_compaction_never_touches_the_transcript(guide, model):
    guide.config.memory.max_history_tokens = 200
    guide.config.memory.keep_turns = 1
    model.script = [say("First answer."), say("## Goal\nloan"), say("Second answer.")]
    state = start(guide, LOAN)
    collect(guide, "h2", message="first question", state=state)
    ev = collect(guide, "h2", message="second question", state=state)
    assert any(e.get("name") == "memory_compacted" for e in ev)
    entries = guide.thread("h2")["transcript"]
    assert [e.get("text") for e in entries if e["kind"] in ("user", "assistant")] == [
        "first question", "First answer.", "second question", "Second answer."]
    assert any(e["kind"] == "notice" for e in entries)


def test_history_survives_a_restart(tmp_path):
    """SQLite checkpointer + file transcripts: a new FormGuide on the same files continues the thread."""
    model = ScriptedChatModel(script=[
        say("", ("t1", "propose_changes", {"changes": [{"name": "loan_type", "value": "mortgage"}]})),
        say("Mortgage selected; the Collateral tab appeared."),
    ])

    def make() -> FormGuide:
        return FormGuide(GuideConfig(models=Models(agent=model), data_dir=tmp_path,
                                     checkpointer=sqlite_checkpointer(tmp_path / "cp.sqlite"),
                                     transcripts=FileTranscriptStore(tmp_path / "tx")))

    async def go():
        g1 = make()
        state = start(g1, LOAN)
        _ = [e async for e in g1.run("r1", message="I want a mortgage", state=state)]

        g2 = make()                                    # "restart": fresh objects, same files
        g2.register_form(LOAN.jsx, LOAN.form_id)       # the frontend re-registers the form on load
        t = g2.thread("r1")
        assert t["pending_card"] and t["transcript"][0]["text"] == "I want a mortgage"
        new_cfg = LOAN.compute({**state["config"]["state"], "loan_type": {"id": "mortgage", "name": "Mortgage"}})
        ev = [e async for e in g2.run("r1", resume={"accepted": True, "config": new_cfg})]
        assert not any(e["type"] == "RUN_ERROR" for e in ev)
        assert [e.get("status") for e in g2.thread("r1")["transcript"] if e["kind"] == "card"] == ["accepted"]
        sent = model.calls[-1]
        assert any(isinstance(m, ToolMessage) and "confirmed" in m.content for m in sent)
        await g2.delete_thread("r1")
        assert g2.thread("r1")["transcript"] == []
        assert (await g2.history("r1")) == []

    asyncio.run(go())


def test_thread_endpoints(guide, model):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from formguide.server import create_router

    app = FastAPI()
    app.include_router(create_router(guide), prefix="/agent")
    c = TestClient(app)
    model.script = [say("Hello!")]
    collect(guide, "h3", message="hi", state=start(guide, LOAN))
    r = c.get("/agent/threads/h3").json()
    assert [e["kind"] for e in r["transcript"]] == ["user", "assistant"] and r["pending_card"] is None
    assert c.get("/agent/threads/..%2Fetc").status_code in (400, 404)
    assert c.delete("/agent/threads/h3").status_code == 200 and c.get("/agent/threads/h3").json()["transcript"] == []
