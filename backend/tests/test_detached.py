"""Turns that outlive the connection (http-api, chat-history): a reload or a closed tab does not lose the answer."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from pydantic import Field

from demo.mock_forms import FORMS
from formguide import FormGuide, GuideConfig, Models

from .conftest import ScriptedChatModel, say
from .test_agent import start

LOAN = FORMS["loan_application"]


class GatedModel(ScriptedChatModel):
    """Answers only when the test opens the gate: the turn is "still running" until then."""
    gate: Any = Field(default=None)

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        await self.gate.wait()
        for chunk in self._stream(messages, stop, run_manager, **kwargs):
            yield chunk


def gated(tmp_path) -> tuple[FormGuide, GatedModel]:
    m = GatedModel(gate=asyncio.Event())
    return FormGuide(GuideConfig(models=Models(agent=m), data_dir=tmp_path)), m


def test_a_turn_finishes_after_the_client_goes_away(tmp_path):
    async def go():
        guide, model = gated(tmp_path)
        model.script = [say("Your loan type is set.")]
        stream = guide.run_detached(thread_id="d1", message="car loan please", state=start(guide, LOAN))
        first = await anext(stream)                       # the client got the start of the turn...
        assert first["type"] == "RUN_STARTED"
        await stream.aclose()                             # ...and went away (reload, closed tab)
        assert guide.running("d1") and guide.thread("d1")["running"] is True
        texts = [e.get("text") for e in guide.thread("d1")["transcript"]]
        assert texts == ["car loan please"]               # restore now: the question, the answer still coming
        model.gate.set()
        for _ in range(100):
            if not guide.running("d1"):
                break
            await asyncio.sleep(0.02)
        t = guide.thread("d1")
        assert t["running"] is False
        assert [e.get("text") for e in t["transcript"] if e["kind"] in ("user", "assistant")] == [
            "car loan please", "Your loan type is set."]
    asyncio.run(go())


def test_stop_ends_a_running_turn_and_the_next_turn_waits_for_one(tmp_path):
    async def go():
        guide, model = gated(tmp_path)
        model.script = [say("first"), say("second")]
        state = start(guide, LOAN)
        one = guide.run_detached(thread_id="d2", message="one", state=state)
        await anext(one)
        assert guide.stop("d2") is True
        await asyncio.sleep(0.01)
        assert not guide.running("d2")
        assert guide.stop("d2") is False                  # nothing left to stop
        # a turn that is still running: the next one waits for it, then runs
        three = guide.run_detached(thread_id="d2", message="two", state=state)
        await anext(three)
        four = guide.run_detached(thread_id="d2", message="three", state=state)
        waiting = asyncio.create_task(anext(four))
        await asyncio.sleep(0.05)
        assert not waiting.done()                          # waits for "two"
        model.gate.set()
        async for _ in three:
            pass
        assert (await asyncio.wait_for(waiting, 2))["type"] == "RUN_STARTED"
        async for _ in four:
            pass
    asyncio.run(go())


def test_the_router_has_stop_and_says_running(guide, model):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from formguide.server import create_router
    app = FastAPI()
    app.include_router(create_router(guide), prefix="/agent")
    c = TestClient(app)
    assert c.post("/agent/stop", json={"thread_id": "nope"}).json() == {"stopped": False}
    body = c.get("/agent/threads/nope?format=agui").json()
    assert body["running"] is False
    assert json.dumps(body)
