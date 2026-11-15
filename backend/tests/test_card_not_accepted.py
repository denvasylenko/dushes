"""A value the form refuses is not an answered card: the card is marked not accepted, with the form's reason."""
from __future__ import annotations

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, ask, tool_result


def _results(ev):
    return [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "card_result"]


def test_a_value_the_form_refuses_marks_the_card_not_accepted(guide, model):
    v, state, _ = ask(guide, model, "na1", {"question": "Your first name?", "field": "first_name"})
    cfg = {**state["config"], "state": {**state["config"]["state"], "first_name": "5"},
           "props": {**state["config"]["props"],
                     "first_name": {**state["config"]["props"]["first_name"], "error": "Letters only, at least 2"}}}
    model.script = [say("The name was not accepted: letters only, at least two. What is your first name?")]
    ev = collect(guide, "na1", resume={"answer": {"text": "5"}, "config": cfg})
    got = _results(ev)
    assert got == [{"status": "not_accepted", "reason": "Letters only, at least 2", "field": "first_name",
                    "card_id": v["card_id"]}]
    out = tool_result(model, "q1")
    assert "The form did not accept it for First name" in out and "Letters only, at least 2" in out
    assert "This filled the field" not in out and "is not filled" in out
    q = next(e for e in guide.thread("na1")["transcript"] if e["kind"] == "question")
    assert q["status"] == "not_accepted" and q["reason"] == "Letters only, at least 2"      # a reload shows the same


def test_an_accepted_value_sends_no_such_event(guide, model):
    _, state, _ = ask(guide, model, "na2", {"question": "Your first name?", "field": "first_name"})
    cfg = {**state["config"], "state": {**state["config"]["state"], "first_name": "Anna"}}
    model.script = [say("Thanks.")]
    ev = collect(guide, "na2", resume={"answer": {"text": "Anna"}, "config": cfg})
    assert _results(ev) == [] and "This filled the field First name" in tool_result(model, "q1")
    q = next(e for e in guide.thread("na2")["transcript"] if e["kind"] == "question")
    assert q["status"] == "answered"
