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
    assert site.route("when is the branch open on Saturday?", st) == "unclear"                  # another page's words:
    assert site.route("I'd also like a haircut", st) == "unclear"                               # the model decides
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


def test_files_uploaded_on_a_form_page_reach_the_form_agent(site, guide, monkeypatch):
    site_thread = "7b1f0c2e-1d3a-4c5b-9e8f-0a1b2c3d4e5f"   # a real chat id: the form thread is 53 chars with "_"
    att = guide.attachments.save(site_thread, "passport.jpg", b"\xff\xd8 scan")
    up = guide.attachments.save(site_thread, "payslip.pdf", b"%PDF scan")
    seen = {}

    async def fake_run(thread_id, **kw):
        seen["thread_id"] = thread_id
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": "r"}
    monkeypatch.setattr(site.forms, "run", fake_run)
    st = form_state(guide)
    st["form"]["attachments"] = [att]
    run(site, site_thread, message="read my passport", state=st)
    form_thread = seen["thread_id"]
    assert form_thread == f"{site_thread}-loan_application"
    assert guide.attachments.load(form_thread, att["id"])[0] == "passport.jpg"     # carried over, same id
    run(site, site_thread, resume={"attachment_ids": [up["id"]]}, state=form_state(guide))
    assert guide.attachments.load(form_thread, up["id"])[0] == "payslip.pdf"       # an upload card's file too


def test_attachment_threads_follow_the_chat_rule(guide):
    long_id = "a" * 60 + "-loan_application"
    saved = guide.attachments.save(long_id, "x.pdf", b"%PDF")
    assert guide.attachments.load(long_id, saved["id"])
    import pytest as _pt
    with _pt.raises(ValueError):
        guide.attachments.save("bad id!", "x.pdf", b"%PDF")


def test_the_site_agent_reads_the_site_documents(site, guide, model):
    guide.add_document("site", "partners.md", b"# Partners\n## Keystone Valuation\nKeystone is the appraiser the bank accepts.")
    model.script = [say("Keystone Valuation is the bank's appraiser (Partners).")]
    run(site, "k1", message="what is Keystone Valuation?", state={"page": {"path": "/"}})
    system = model.calls[0][0].content
    assert "Keystone is the appraiser" in system                       # document passages, not only the site map
    assert "general knowledge" in system                               # general concepts allowed, marked as general
    assert "ask_documents" in {(t.get("function") or t)["name"] if isinstance(t, dict) else t.name for t in model.bound}
    assert set(guide.knowledge.namespaces_for("site")) >= {"site", "loan_application", "barber_booking"}


def test_one_transcript_and_restore(site, guide, model, monkeypatch):
    async def fake_run(thread_id, **kw):
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "Car loan noted."}
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": "r"}
    model.script = [say("Hi! Ask me anything."), say("form")]     # the second: the router's one word
    run(site, "k2", message="hello", state={"page": {"path": "/"}})
    monkeypatch.setattr(site.forms, "run", fake_run)
    run(site, "k2", message="a car loan please", state=form_state(guide))
    t = site.thread("k2", "loan_application")
    assert [(m["role"], m["content"]) for m in t["messages"]] == [
        ("user", "hello"), ("assistant", "Hi! Ask me anything."), ("user", "a car loan please"), ("assistant", "Car loan noted.")]
    assert t["pending_card"] is None


def test_the_hand_off_note_survives_a_restart(guide, model, monkeypatch):
    first = SiteGuide(guide, SiteMap.load(SITE))
    model.script = [say("", ("o1", "open_form", {"form_id": "loan_application", "note": "A cash loan of 200 000."})),
                    say("Opening it.")]
    run(first, "k3", message="I need 200 000 in cash", state={"page": {"path": "/"}})
    restarted = SiteGuide(guide, SiteMap.load(SITE))                      # a new process: nothing in memory
    seen = {}

    async def fake_run(thread_id, **kw):
        seen.update(kw)
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": "r"}
    monkeypatch.setattr(restarted.forms, "run", fake_run)
    run(restarted, "k3", state=form_state(guide), handoff=True)
    assert seen["message"].endswith("A cash loan of 200 000.")



def test_an_unclear_message_is_decided_by_the_router_model(site, guide, model, monkeypatch):
    seen = []

    async def fake_run(thread_id, **kw):
        seen.append("form")
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": "r"}
    monkeypatch.setattr(site.forms, "run", fake_run)
    model.script = [say("form")]
    run(site, "k4", message="a car loan please", state=form_state(guide))
    assert seen == ["form"]                                            # the model said form
    model.script = [say("site"), say("The barbershop prices are on the Barbershop page.")]
    run(site, "k4", message="what are the barbershop prices?", state=form_state(guide))
    assert seen == ["form"]                                            # the model said site: the site agent answered
    prompt = model.calls[-2][0].content
    assert "Answer with one word" in prompt and "loan_application" in prompt


def test_the_business_instructions_and_a_last_reply(guide, model):
    m = SiteMap.load({"title": "Shop", "instructions": "Always mention the spring sale.",
                      "pages": [{"path": "/", "title": "Home", "description": "The shop."}]})
    s = SiteGuide(guide, m)
    loop = [say("", (f"q{i}", "search_site", {"query": "sale"})) for i in range(4)]
    model.script = [*loop, say("I could not find more about the sale.")]
    ev = run(s, "k5", message="tell me about the sale", state={"page": {"path": "/"}})
    system = model.calls[0][0].content
    assert "Always mention the spring sale." in system and "Priorities" in system
    assert "could not find more" in "".join(e.get("delta", "") for e in ev)       # the rounds ran out: a reply anyway
    assert "Do not call tools now" in model.calls[-1][-1].content


def test_navigate_tells_the_model_what_the_part_shows():
    told, _d = directive(SiteMap.load(SITE), {"path": "/contacts", "section": "barber"})
    assert "10:00 to 21:00" in told


def test_host_context_tools_and_style(guide, model):
    from formguide.site import SiteTool
    seen = {}

    def stats(args, ctx):
        seen.update(args=args, host=ctx.host, page=ctx.page)
        return "Visits this week: 120."

    async def live(ctx):
        return f"Open today 12:00 to 23:00 ({ctx.host['site']})."
    s = SiteGuide(guide, SiteMap.load(SITE), context=live, instructions="Call the owner by name.",
                  style="Reply in up to five sentences.", history=2,
                  tools=[SiteTool("site_stats", "Visits.", {"type": "object", "properties": {"days": {"type": "string"}}}, stats)])
    model.script = [say("", ("t1", "site_stats", {"days": "7"})), say("120 visits this week.")]
    ev = run(s, "h1", message="how many visits?", state={"page": {"path": "/"}}, host={"site": "Trattoria"})
    system = model.calls[0][0].content
    assert "Open today 12:00 to 23:00 (Trattoria)." in system and "Call the owner by name." in system
    assert "Reply in up to five sentences." in system and "one to three short sentences" not in system
    assert seen == {"args": {"days": "7"}, "host": {"site": "Trattoria"}, "page": "/"}
    assert "Visits this week: 120." in [e["content"] for e in ev if e["type"] == "TOOL_CALL_RESULT"][0]


def test_a_failing_host_tool_does_not_end_the_turn(guide, model):
    from formguide.site import SiteTool

    def boom(args, ctx):
        raise RuntimeError("db down")
    s = SiteGuide(guide, SiteMap.load(SITE), tools=[SiteTool("site_stats", "Visits.", {"type": "object", "properties": {}}, boom)])
    model.script = [say("", ("t1", "site_stats", {})), say("I could not check the visits right now.")]
    ev = run(s, "h2", message="visits?", state={"page": {"path": "/"}})
    assert "tool failed" in [e["content"] for e in ev if e["type"] == "TOOL_CALL_RESULT"][0]
    assert ev[-1]["type"] == "RUN_FINISHED" and not any(e["type"] == "RUN_ERROR" for e in ev)


def test_suggestions_from_the_site_agent(guide, model):
    s = SiteGuide(guide, SiteMap.load(SITE), suggestions=True)
    model.script = [say("Barber & Co is open every day 10:00 to 21:00.",
                        ("g1", "suggest_next", {"options": ["Book a haircut", "Show prices"]}))]
    ev = run(s, "h3", message="when is the barber open?", state={"page": {"path": "/"}})
    assert [e["value"] for e in ev if e.get("name") == "suggestions"] == [{"items": ["Book a haircut", "Show prices"]}]


def test_hand_off_in_the_same_run(guide, model, monkeypatch):
    built = {}

    def form_for(form_id, ctx):
        built.update(form_id=form_id, host=ctx.host)
        return {"form_id": form_id, "config": {}, "jsx_hash": "x"}
    s = SiteGuide(guide, SiteMap.load(SITE), form_for=form_for)
    seen = {}

    async def fake_run(thread_id, **kw):
        seen.update(thread_id=thread_id, **kw)
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": kw["run_id"]}
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "Here is the service:"}
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": kw["run_id"]}
    monkeypatch.setattr(s.forms, "run", fake_run)
    model.script = [say("", ("o1", "open_form", {"form_id": "barber_booking", "note": "A haircut on Friday.",
                                                 "language": "Russian"}))]
    ev = run(s, "h4", message="book me a haircut on Friday", state={"page": {"path": "/"}}, host="me")
    types = [e["type"] for e in ev]
    assert types.count("RUN_STARTED") == 1 and types.count("RUN_FINISHED") == 1 and types[-1] == "RUN_FINISHED"
    assert [e["value"] for e in ev if e.get("name") == "site_directive"] == [
        {"type": "navigate", "path": "/book", "form_id": "barber_booking", "handoff": "done"}]
    assert built == {"form_id": "barber_booking", "host": "me"} and seen["thread_id"] == "h4-barber_booking"
    assert seen["message"].endswith("A haircut on Friday. Reply to the user in Russian.")
    assert len(model.calls) == 1                                          # the site agent says nothing after open_form
    seen.clear()
    run(s, "h4", state={"page": {"path": "/book"}, "form": {"form_id": "barber_booking"}}, handoff=True)
    assert seen["message"] is None                                        # the page's run finds no pending note
    assert site_messages(s, "h4")[-1] == ("assistant", "Here is the service:")


def site_messages(s, thread):
    return [(m["role"], m["content"]) for m in s.thread(thread)["messages"]]


def test_the_page_hand_off_carries_the_language(site, guide, model, monkeypatch):
    model.script = [say("", ("o1", "open_form", {"form_id": "loan_application", "note": "A car loan.", "language": "Russian"})),
                    say("Opening it.")]
    run(site, "h5", message="car loan", state={"page": {"path": "/"}})
    seen = {}

    async def fake_run(thread_id, **kw):
        seen.update(kw)
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": "r"}
    monkeypatch.setattr(site.forms, "run", fake_run)
    run(site, "h5", state=form_state(guide), handoff=True)
    assert seen["message"].endswith("A car loan. Reply to the user in Russian.")


def test_routing_by_who_spoke_last(site, guide, model):
    st = form_state(guide)
    from formguide.transcript import new_entry
    tx = site.forms.transcripts
    tx.append("h6", new_entry("assistant", text="Car loan noted.", form_id="loan_application"))
    assert site.route("the second one", st, thread_id="h6") == "form"                # the form spoke last
    tx.append("h6", new_entry("assistant", text="Which one do you mean?"))
    assert site.route("the second one", st, thread_id="h6") == "unclear"             # the site agent spoke last
    open_ru = "\u043e\u0442\u043a\u0440\u043e\u0439 \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u044b"   # "open contacts" in Russian
    tx.append("h6", new_entry("assistant", text="Noted.", form_id="loan_application"))
    assert site.route(open_ru, st, thread_id="h6") == "unclear"                      # navigation in another language
    model.script = [say("site")]
    assert asyncio.run(site.classify("contacts", st, "h6")) == "site"
    assert "The last to speak was the form assistant" in model.calls[-1][0].content


def test_the_router_builds_the_host_per_request(guide, model):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from formguide.site import create_site_router
    got = []
    s = SiteGuide(guide, SiteMap.load(SITE), context=lambda ctx: got.append(ctx.host) or "")
    app = FastAPI()
    app.include_router(create_site_router(s, host=lambda request: request.headers.get("x-site")), prefix="/site")
    model.script = [say("Hi!")]
    body = {"threadId": "h7", "runId": "r1", "messages": [{"role": "user", "content": "hi"}],
            "state": {"page": {"path": "/"}}, "tools": [], "context": [], "forwardedProps": {}}
    TestClient(app).post("/site/run", json=body, headers={"x-site": "trattoria"})
    assert got == ["trattoria"]


def test_questions_about_the_business_go_to_the_router_model(site, guide):
    st = form_state(guide)
    where_ru = "\u0430 \u0433\u0434\u0435 \u0432\u044b \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0435\u0441\u044c?"   # "where are you located?"
    assert site.route("where are you located?", st) == "unclear"
    assert site.route(where_ru, st) == "unclear"
    assert site.route("I want it with Maria", st) == "form"
