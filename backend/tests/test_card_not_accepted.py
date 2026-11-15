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


def test_the_widget_says_the_form_refused_and_sends_no_config(guide, model):
    """What <agui-chat> sends for a typed value the form refuses (the owner's VIN "555"): the old value is back on
    the form, so there is no config, only the answer and the form's own words in `rejected`."""
    v, _, _ = ask(guide, model, "na3", {"question": "Your first name?", "field": "first_name"})
    model.script = [say("The name was not accepted: letters only, at least two. What is your first name?")]
    ev = collect(guide, "na3", resume={"answer": {"text": "5"}, "rejected": {"first_name": "Letters only, at least 2"}})
    assert _results(ev) == [{"status": "not_accepted", "reason": "Letters only, at least 2", "field": "first_name",
                             "card_id": v["card_id"]}]
    out = tool_result(model, "q1")
    assert "The user wrote: 5" in out and "did not accept it" in out and "is not filled" in out
    q = next(e for e in guide.thread("na3")["transcript"] if e["kind"] == "question")
    assert q["status"] == "not_accepted"

    _, _, _ = ask(guide, model, "na4", {"question": "Your first name?", "field": "first_name"})
    model.script = [say("Thanks.")]
    ev = collect(guide, "na4", resume={"answer": {"text": "Anna"}, "rejected": {}})   # nothing refused: as before
    assert _results(ev) == []


def test_a_late_answer_for_a_closed_card_is_refused_and_an_unknown_id_is_not(guide, model):
    """An answer names its card. One for a card of this conversation that is no longer open changes nothing and is
    answered with card_result; an id the conversation never had (another client's own numbering) is taken as before."""
    first, state, _ = ask(guide, model, "late1", {"question": "Your first name?", "field": "first_name"})
    model.script = [say("", ("q2", "ask_user", {"question": "Which loan?", "options": ["Car loan", "Mortgage"]}))]
    collect(guide, "late1", message="are you there?", state=state)             # the first card closes, a second opens
    calls = len(model.calls)
    ev = collect(guide, "late1", resume={"answer": {"text": "Anna"}, "card_id": first["card_id"]})
    assert [e["type"] for e in ev] == ["RUN_STARTED", "CUSTOM", "RUN_FINISHED"] and len(model.calls) == calls
    assert _results(ev) == [{"card_id": first["card_id"], "status": "not_accepted",
                             "reason": "This question is no longer open.", "code": "card_gone"}]
    open_now = [e for e in guide.thread("late1")["transcript"] if e.get("status") == "pending"]
    assert len(open_now) == 1 and open_now[0]["id"] != first["card_id"]         # the open card still waits

    model.script = [say("Thanks.")]
    ev = collect(guide, "late1", resume={"answer": {"text": "Car loan"}, "card_id": "someone-elses-id"})
    assert _results(ev) == [] and len(model.calls) == calls + 1                  # an unknown id: answered as before
