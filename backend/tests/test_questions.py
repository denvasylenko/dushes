"""Question cards (ask_user) and partial acceptance of field-change cards."""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import ToolMessage

from demo.mock_forms import FORMS
from formguide import agui
from formguide.server import create_router

from .conftest import say
from .test_agent import collect, start
from .test_agui import check_order

LOAN = FORMS["loan_application"]


def interrupt_value(ev):
    found = [e for e in ev if e.get("name") == "on_interrupt"]
    return json.loads(found[0]["value"]) if found else None


def tool_result(model, call_id):
    return next(m.content for m in model.calls[-1] if isinstance(m, ToolMessage) and m.tool_call_id == call_id)


def ask(guide, model, thread, args, state=None):
    model.script = [say("", ("q1", "ask_user", args))]
    state = state or start(guide, LOAN)
    ev = collect(guide, thread, message="I want a loan", state=state)
    check_order(ev)
    return interrupt_value(ev), state, ev


def test_question_with_own_options_and_click_answer(guide, model):
    v, state, _ = ask(guide, model, "q1", {"question": "Same address?", "options": ["Yes", "No"]})
    assert v["type"] == "ask" and v["card_id"] and v["question"] == "Same address?"
    assert v["options"] == [{"id": "Yes", "label": "Yes"}, {"id": "No", "label": "No"}]
    assert v["multiple"] is False and v["allow_text"] is True and "field" not in v
    assert guide.thread("q1")["pending_card"]["kind"] == "question"

    model.script = [say("Noted.")]
    collect(guide, "q1", resume={"answer": {"ids": ["No"]}})
    assert tool_result(model, "q1") == "The user chose: No (No)"
    q = next(e for e in guide.thread("q1")["transcript"] if e["kind"] == "question")
    assert q["status"] == "answered" and q["answer"]["ids"] == ["No"]
    assert guide.thread("q1")["pending_card"] is None


def test_question_from_a_field(guide, model):
    v, _, _ = ask(guide, model, "q2", {"question": "Which loan?", "field": "loan_type"})
    assert v["field"] == "loan_type" and len(v["options"]) == 4
    assert {"id": "auto", "label": "Car loan"} in v["options"]

    v, _, _ = ask(guide, model, "q3", {"question": "Which loan?", "field": "loan_type",
                                       "options": ["Car loan", "mortgage"]})
    assert [o["id"] for o in v["options"]] == ["auto", "mortgage"]

    model.script = [say("Ok.")]
    collect(guide, "q3", resume={"answer": {"ids": ["auto"]}})
    assert tool_result(model, "q1") == "The user chose: Car loan (auto)"


def test_question_refusals(guide, model):
    for thread, args, needle in [
        ("r1", {"question": "?", "field": "first_name"}, "not a dropdown"),
        ("r2", {"question": "?", "field": "loan_type", "options": ["boat"]}, "no option 'boat'"),
        ("r3", {"question": "?", "options": [str(i) for i in range(13)]}, "too many options"),
        ("r4", {"question": "?", "allow_text": False}, "must allow a typed answer"),
    ]:
        model.script = [say("", ("q1", "ask_user", args)), say("Let me ask in text.")]
        ev = collect(guide, thread, message="hi", state=start(guide, LOAN))
        assert interrupt_value(ev) is None
        assert needle in tool_result(model, "q1")


def test_typed_string_and_skipped_answers(guide, model):
    for thread, resume, expected in [
        ("s1", {"answer": {"text": "only on weekends"}}, "The user wrote: only on weekends"),
        ("s2", agui.run_kwargs({"threadId": "s2", "messages": [], "forwardedProps": {
            "command": {"resume": "only on weekends"}}})["resume"], "The user wrote: only on weekends"),
        ("s3", agui.run_kwargs({"threadId": "s3", "messages": [], "resume": [
            {"interrupt_id": "x", "status": "cancelled"}]})["resume"], "The user skipped the question."),
        ("s4", {"answer": {"ids": ["Maybe"]}}, "was not one of the options"),
        ("s5", {"answer": {"ids": ["Yes", "No"]}}, "single-choice"),
    ]:
        ask(guide, model, thread, {"question": "Same address?", "options": ["Yes", "No"]})
        model.script = [say("Ok.")]
        collect(guide, thread, resume=resume)
        assert expected in tool_result(model, "q1"), thread
        q = next(e for e in guide.thread(thread)["transcript"] if e["kind"] == "question")
        assert q["status"] == ("answered" if "wrote" in expected else "dismissed")


def test_multiple_choice(guide, model):
    v, _, _ = ask(guide, model, "m1", {"question": "Which contacts?", "options": ["SMS", "Email", "Post"],
                                       "multiple": True})
    assert v["multiple"] is True
    model.script = [say("Ok.")]
    collect(guide, "m1", resume={"answer": {"ids": ["SMS", "Email"]}})
    assert tool_result(model, "q1") == "The user chose: SMS (SMS), Email (Email)"


def test_one_waiting_interaction_per_step(guide, model):
    tools = [{"name": "highlightField", "description": "Flash a field"}]
    model.script = [say("", ("q1", "ask_user", {"question": "Which?", "options": ["A", "B"]}),
                        ("t2", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]}),
                        ("c3", "highlightField", {}))]
    ev = collect(guide, "w1", message="hi", state=start(guide, LOAN), client_tools=tools)
    assert interrupt_value(ev)["type"] == "ask"
    results = {e["toolCallId"]: e["content"] for e in ev if e["type"] == "TOOL_CALL_RESULT"}
    assert "already waiting" in results["t2"] and "Not executed" in results["c3"]


def test_ignored_question_and_structured_outcome(guide, model):
    ask(guide, model, "i1", {"question": "Same address?", "options": ["Yes", "No"]})
    model.script = [say("Sure.")]
    collect(guide, "i1", message="never mind", state=start(guide, LOAN))
    assert "did not answer the question" in tool_result(model, "q1")
    assert next(e for e in guide.thread("i1")["transcript"] if e["kind"] == "question")["status"] == "dismissed"

    guide.config.interrupt_mode = "structured"
    _, _, ev = ask(guide, model, "i2", {"question": "Which loan?", "field": "loan_type"})
    out = ev[-1]["outcome"]["interrupts"][0]
    assert out["reason"] == "ask_user" and out["message"] == "Which loan?"
    assert out["metadata"]["field"] == "loan_type" and len(out["metadata"]["options"]) == 4
    assert out["id"] == guide.thread("i2")["pending_card"]["id"]


def test_question_restored_through_the_router(guide, model):
    ask(guide, model, "h1", {"question": "Same address?", "options": ["Yes", "No"]})
    app = FastAPI()
    app.include_router(create_router(guide), prefix="/agent")
    pending = TestClient(app).get("/agent/threads/h1").json()["pending_card"]
    assert pending["kind"] == "question" and pending["options"][0]["id"] == "Yes"


# ---------------------------------------------------------------- partial acceptance

CHANGES = [{"name": "first_name", "value": "Anna"}, {"name": "last_name", "value": "Ivanova"},
           {"name": "gender", "value": "Female"}]


def card(guide, model, thread):
    model.script = [say("", ("t1", "propose_changes", {"changes": CHANGES}))]
    state = start(guide, LOAN)
    ev = collect(guide, thread, message="I am Anna Ivanova", state=state)
    return interrupt_value(ev), state


def test_partial_acceptance(guide, model):
    _, state = card(guide, model, "p1")
    cfg = LOAN.compute({**state["config"]["state"], "first_name": "Anna", "last_name": "Ivanova"})
    model.script = [say("Done.")]
    collect(guide, "p1", resume={"accepted": True, "names": ["first_name", "last_name", "nope"], "config": cfg})
    text = tool_result(model, "t1")
    assert "The user applied: first_name, last_name. Declined (not applied): gender." in text
    c = next(e for e in guide.thread("p1")["transcript"] if e["kind"] == "card")
    assert c["status"] == "partial" and c["names"] == ["first_name", "last_name"]


def test_partial_acceptance_edge_cases(guide, model):
    card(guide, model, "p2")
    model.script = [say("Ok.")]
    collect(guide, "p2", resume={"accepted": True, "names": []})
    assert tool_result(model, "t1").startswith("The user rejected the changes.")
    assert next(e for e in guide.thread("p2")["transcript"] if e["kind"] == "card")["status"] == "rejected"

    _, state = card(guide, model, "p3")
    model.script = [say("Ok.")]
    collect(guide, "p3", resume={"accepted": True, "config": state["config"]})
    assert tool_result(model, "t1").startswith("The user confirmed; changes applied.")
    assert next(e for e in guide.thread("p3")["transcript"] if e["kind"] == "card")["status"] == "accepted"

    card(guide, model, "p4")      # a text-only client answering "ok"
    model.script = [say("Ok.")]
    collect(guide, "p4", resume=agui.run_kwargs({"threadId": "p4", "messages": [], "forwardedProps": {
        "command": {"resume": "ok"}}})["resume"])
    assert tool_result(model, "t1").startswith("The user confirmed")
