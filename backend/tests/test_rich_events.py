"""Confirm details, the receipt and sources events, feedback, the privacy note."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.tools import tool

from formguide.knowledge.research import parse_sources
from formguide.server import create_router

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value


def customs(ev, name):
    return [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == name]


def test_confirm_details_and_consequence(guide, model):
    model.script = [say("", ("k1", "confirm_action", {
        "title": "Send the application", "message": "To the bank.", "consequence": "You can't edit it after sending.",
        "details": [{"label": "Car loan", "value": "1 500 000"}, {"label": "", "value": "x"}]}))]
    v = interrupt_value(collect(guide, "e1", message="send it", state=start(guide, LOAN)))
    assert v["details"] == [{"label": "Car loan", "value": "1 500 000"}]
    assert v["consequence"] == "You can't edit it after sending."


def test_receipt_after_a_confirmed_host_tool(guide, model):
    @tool
    def submit_application() -> dict:
        """Submit the application."""
        return {"ok": True, "receipt": {"number": "A-118", "eta": "within a day", "secret": "x"}}

    guide._tools.append(submit_application)
    guide.config.confirm_tools = ["submit_application"]
    model.script = [say("", ("s1", "submit_application", {}))]
    ev = collect(guide, "e2", message="submit", state=start(guide, LOAN))
    card = interrupt_value(ev)
    model.script = [say("Sent.")]
    ev = collect(guide, "e2", resume={"accepted": True})
    rec = customs(ev, "receipt")
    assert rec == [{"number": "A-118", "eta": "within a day", "card_id": card["card_id"]}]
    entry = next(e for e in guide.thread("e2")["transcript"] if e["kind"] == "confirm")
    assert entry["receipt"]["number"] == "A-118"


def test_sources_parsed_and_sent_once(guide, model, monkeypatch):
    assert parse_sources("x\nSources: a.md › Rates; b.md") == [{"title": "a.md", "section": "Rates"},
                                                                    {"title": "b.md"}]
    assert parse_sources("no sources here") == []

    async def fake(*a, **k):
        return "Free of charge.\nSources: tariffs_2026.md › Early repayment"
    from formguide.knowledge import research
    monkeypatch.setattr(research, "ask_documents", fake)
    guide.knowledge.add_document("loan_application", "tariffs_2026.md", b"# Tariffs\n## Early repayment\nFree.")
    model.script = [say("", ("d1", "ask_documents", {"question": "fees?"})), say("It is free.")]
    ev = collect(guide, "e3", message="fees?", state=start(guide, LOAN))
    got = customs(ev, "sources")
    assert got == [{"items": [{"title": "tariffs_2026.md", "section": "Early repayment"}]}]
    names = [e.get("name") or e["type"] for e in ev]
    assert names.index("sources") > max(i for i, n in enumerate(names) if n == "TEXT_MESSAGE_END")


def test_feedback_endpoint(guide):
    app = FastAPI()
    app.include_router(create_router(guide), prefix="/agent")
    c = TestClient(app)
    assert c.post("/agent/feedback", json={"thread_id": "e4", "value": 1, "card_id": "k"}).status_code == 204
    assert c.post("/agent/feedback", json={"thread_id": "e4", "value": 5}).status_code == 422
    assert c.post("/agent/feedback", json={"thread_id": "e4", "value": True}).status_code == 422
    fb = [e for e in guide.thread("e4")["transcript"] if e["kind"] == "feedback"]
    assert fb and fb[0]["value"] == 1 and fb[0]["card_id"] == "k"


def test_privacy_note_on_upload_requests(guide, model):
    guide.config.privacy_note = "Your file stays on our server."
    model.script = [say("", ("u1", "request_file", {"prompt": "A photo of your passport"}))]
    v = interrupt_value(collect(guide, "e5", message="hi", state=start(guide, LOAN)))
    assert v["privacy"] == "Your file stays on our server."
