"""SiteGuide: routing between the site agent and the form agent, navigation checks, the hand-off."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from formguide.site import SiteGuide, SiteMap
from formguide.site.agent import directive

from .conftest import say
from .test_agent import start
from .test_questions import LOAN

SITE = Path(__file__).resolve().parents[1] / "demo" / "site.yaml"


@pytest.fixture
def site(guide):
    return SiteGuide(guide, SiteMap.load(SITE))


def run(site, thread, **kw):
    async def go():
        return [e async for e in site.run(thread, **kw)]
    return asyncio.run(go())


def form_state(guide, path="/apply"):
    return {"page": {"path": path}, "form": start(guide, LOAN)}


def test_routing(site, guide):
    st = form_state(guide)
    assert site.route("what does a mortgage need?", {"page": {"path": "/faq"}}) == "site"       # no form: site
    assert site.route("my name is Anna Smith", st) == "form"
    assert site.route("the loan amount is 900 000", st) == "form"                              # the page's own words
    assert site.route("open the contacts page", st) == "site"
    assert site.route("when is the branch open on Saturday?", st) == "site"                     # another page's words
    assert site.route("I'd also like a haircut", st) == "site"
    booking = {"page": {"path": "/book"}, "form": {"form_id": "barber_booking"}}
    assert site.route("book me a haircut tomorrow at 3", booking) == "form"                     # haircut is this page's
    assert site.route(None, st, resume={"accepted": True}) == "form"                            # cards: the form agent
    assert site.route(None, st, handoff=True) == "form"


def test_navigation_is_checked_against_the_map():
    m = SiteMap.load(SITE)
    assert directive(m, {"path": "/loans", "tab": "mortgage"})[1] == {"type": "navigate", "path": "/loans", "tab": "mortgage"}
    assert directive(m, {"path": "/faq", "tab": "early"})[1]["tab"] == "early"                 # an accordion opens as a tab
    assert directive(m, {"path": "/contacts", "section": "bank"})[1]["section"] == "bank"
    told, d = directive(m, {"path": "/careers"})
    assert d is None and "no page" in told
    told, d = directive(m, {"path": "/loans", "tab": "crypto"})
    assert d is None and "no tab" in told


def test_the_site_agent_answers_and_navigates(site, model):
    model.script = [say("", ("n1", "navigate", {"path": "/contacts", "section": "bank"})),
                    say("The branch is open on Saturday 10:00 to 16:00 (Contacts).")]
    ev = run(site, "s1", message="when is the bank open on Saturday?", state={"page": {"path": "/"}})
    d = [e["value"] for e in ev if e.get("name") == "site_directive"]
    assert d == [{"type": "navigate", "path": "/contacts", "section": "bank"}]
    assert "Contacts" in "".join(e.get("delta", "") for e in ev)
    system = model.calls[0][0].content
    assert "/contacts | Contacts" in system and "10:00 to 16:00" in system                     # contents and passages
    hist = site.forms.transcripts.list("s1")
    assert [e["kind"] for e in hist] == ["user", "assistant"]


def test_an_invented_page_is_refused(site, model):
    model.script = [say("", ("n1", "navigate", {"path": "/careers"})), say("There is no careers page.")]
    ev = run(site, "s2", message="open careers", state={"page": {"path": "/"}})
    assert not [e for e in ev if e.get("name") == "site_directive"]
    result = next(e["content"] for e in ev if e["type"] == "TOOL_CALL_RESULT")
    assert "no page" in result


def test_hand_off_to_the_form(site, guide, model, monkeypatch):
    model.script = [say("", ("o1", "open_form", {"form_id": "loan_application",
                                                 "note": "A car loan of 900 000 for 3 years."})),
                    say("Opening the loan application.")]
    ev = run(site, "s3", message="I want a car loan of 900 000 for 3 years", state={"page": {"path": "/"}})
    assert [e["value"] for e in ev if e.get("name") == "site_directive"] == [
        {"type": "navigate", "path": "/apply", "form_id": "loan_application"}]

    seen = {}

    async def fake_run(thread_id, **kw):
        seen.update(thread_id=thread_id, **kw)
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": "r"}
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": "r"}
    monkeypatch.setattr(site.forms, "run", fake_run)
    run(site, "s3", state=form_state(guide), handoff=True)
    assert seen["thread_id"] == "s3-loan_application"
    assert seen["message"].endswith("On the site the user said: A car loan of 900 000 for 3 years.")
    seen.clear()
    run(site, "s3", state=form_state(guide), handoff=True)                                      # used once
    assert seen["message"] is None
    run(site, "s3", message="my name is Anna", state=form_state(guide))
    assert seen["message"] == "my name is Anna" and seen["thread_id"] == "s3-loan_application"


def test_the_map_endpoint_and_run(site, model):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from formguide.site import create_site_router

    app = FastAPI()
    app.include_router(create_site_router(site), prefix="/site")
    c = TestClient(app)
    m = c.get("/site/map").json()
    assert m["title"] == "Main Street" and any(p["form"] == "barber_booking" for p in m["pages"])
    model.script = [say("Hi! Ask me about loans or haircuts.")]
    body = {"threadId": "s4", "runId": "r1", "messages": [{"role": "user", "content": "hi"}],
            "state": {"page": {"path": "/"}}, "tools": [], "context": [], "forwardedProps": {}}
    text = c.post("/site/run", json=body).text
    assert "RUN_FINISHED" in text and "Ask me about loans" in text
