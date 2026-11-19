"""A tool for the UI agent when the conversation runs under the site agent (the owner's question, 2026-11-19: "it's
not possible to expose a tool to the UI agent when using the site agent"). It is: a server tool goes into the form
guide's own configuration, a browser tool comes with the run, and both reach the UI agent whether the run comes
through the mounted route or the host calls site.run() itself. `Dushes(tools=...)` is another thing: those are the
site agent's own tools."""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.tools import tool

from .conftest import say
from .test_site import form_state, run, site  # noqa: F401 - the fixture

PAGE_TOOL = {"name": "get_basket", "description": "What is in the person's basket on this page.",
             "parameters": {"type": "object", "properties": {}}}


@tool
def credit_score(customer: str) -> str:
    """The customer's credit score from the bank's own system."""
    return f"{customer}: 742"


def _names(model):
    """The tools the model was offered in its last call, by name."""
    return {str(getattr(t, "name", None) or (t.get("function") or t).get("name")) for t in model.bound}


def test_a_server_tool_and_a_browser_tool_reach_the_ui_agent_through_site_run(site, guide, model):
    guide._tools.append(credit_score)   # what `tools:` in formguide.yaml or GuideConfig(tools=...) fills
    st = form_state(guide)
    # the UI agent calls the server tool: it runs on the server and its result goes back to the model in this run
    model.script = [say("", ("s1", "credit_score", {"customer": "Anna Smith"})), say("Your score is 742.")]
    ev = run(site, "ut1", message="my name is Anna Smith, what is my credit score", state=st, client_tools=[PAGE_TOOL])
    assert {"credit_score", "get_basket"} <= _names(model)                  # both are offered to the UI agent
    assert any("Anna Smith: 742" in str(getattr(m, "content", "")) for m in model.calls[-1])
    assert "Your score is 742." in "".join(e.get("delta", "") for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")

    # the UI agent calls the browser tool: the run ends with the call for the page to carry out ...
    model.script = [say("", ("c1", "get_basket", {}))]
    ev = run(site, "ut1", message="the loan amount is what is in my basket", state=st, client_tools=[PAGE_TOOL])
    calls = [e for e in ev if e["type"] == "TOOL_CALL_START"]
    assert [c["toolCallName"] for c in calls] == ["get_basket"] and ev[-1]["type"] == "RUN_FINISHED"
    # ... and the page's answer, sent with no message, goes back to the UI agent, not to the site agent
    model.script = [say("Your basket holds 900 000.")]
    ev = run(site, "ut1", state=st, client_tools=[PAGE_TOOL], tool_results={calls[0]["toolCallId"]: '{"total": 900000}'})
    assert any('{"total": 900000}' in str(getattr(m, "content", "")) for m in model.calls[-1])
    assert "Your basket holds 900 000." in "".join(e.get("delta", "") for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")


def test_the_same_through_the_mounted_route(site, guide, model):
    from formguide.site import create_dushes_router
    guide._tools.append(credit_score)   # what `tools:` in formguide.yaml or GuideConfig(tools=...) fills
    app = FastAPI()
    app.include_router(create_dushes_router(site), prefix="/site")
    c, st = TestClient(app), form_state(guide)
    body = {"threadId": "ut2", "runId": "r1", "state": st, "context": [], "forwardedProps": {}, "tools": [PAGE_TOOL],
            "messages": [{"id": "m1", "role": "user", "content": "the loan amount is what is in my basket"}]}
    model.script = [say("", ("c1", "get_basket", {}))]
    text = c.post("/site/run", json=body).text
    assert {"credit_score", "get_basket"} <= _names(model) and '"toolCallName":"get_basket"' in text.replace(" ", "")
    call_id = next(json.loads(line[5:])["toolCallId"] for line in text.splitlines()
                   if line.startswith("data:") and '"TOOL_CALL_START"' in line)
    model.script = [say("Your basket holds 900 000.")]
    body = {**body, "runId": "r2", "messages": [*body["messages"],
            {"id": "m2", "role": "assistant", "content": "", "toolCalls": [
                {"id": call_id, "type": "function", "function": {"name": "get_basket", "arguments": "{}"}}]},
            {"id": "m3", "role": "tool", "toolCallId": call_id, "content": '{"total": 900000}'}]}
    text = c.post("/site/run", json=body).text
    assert "Your basket holds 900 000." in text
    assert any('{"total": 900000}' in str(getattr(m, "content", "")) for m in model.calls[-1])


def test_a_tool_held_for_a_yes_is_held_under_the_site_agent_too(site, guide, model):
    guide._tools.append(credit_score)
    guide.config.confirm_tools = [*(guide.config.confirm_tools or []), "credit_score"]
    model.script = [say("", ("s1", "credit_score", {"customer": "Anna Smith"}))]
    ev = run(site, "ut3", message="my name is Anna Smith, check my credit score", state=form_state(guide))
    cards = [json.loads(e["value"]) if isinstance(e["value"], str) else e["value"]
             for e in ev if e.get("name") == "on_interrupt"]
    assert cards and cards[0]["type"] == "confirm" and "credit_score" in json.dumps(cards[0])
    assert not any("742" in str(getattr(m, "content", "")) for call in model.calls for m in call)   # not run yet


def test_the_same_name_on_both_sides_is_said_at_start_up(guide, caplog):
    from formguide.site import Dushes, SiteMap, SiteTool
    from .test_site import SITE
    guide._tools.append(credit_score)
    with caplog.at_level("WARNING"):
        Dushes(guide, SiteMap.load(SITE), tools=[SiteTool(name="credit_score", description="x", parameters={"type": "object", "properties": {}}, handler=lambda args, ctx: "x")])
    assert "each have a tool named ['credit_score']" in caplog.text
