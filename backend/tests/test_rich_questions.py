"""Richer question payloads: option details, comparisons, long lists, ranges, address, several fields."""
from __future__ import annotations

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value, tool_result


def ask(guide, model, thread, args, state=None, caps=None):
    model.script = [say("", ("q1", "ask_user", args))]
    state = state or start(guide, LOAN)
    ev = collect(guide, thread, message="I want a loan", state=state, capabilities=caps)
    return interrupt_value(ev), state


def test_option_details_and_comparison(guide, model):
    v, _ = ask(guide, model, "r1", {"question": "Which loan?", "recommended": "car", "options": [
        {"id": "car", "label": "Car loan", "description": "from 16.9%", "attrs": {"Rate": "16.9%", "Term": "7 y"}},
        {"id": "cash", "label": "Cash loan", "description": "no collateral", "attrs": {"Rate": "19.9%", "Term": "5 y"}}]})
    assert v["options"][0]["description"] == "from 16.9%" and v["options"][1]["attrs"]["Rate"] == "19.9%"
    assert v["recommended"] == "car"
    v, _ = ask(guide, model, "r2", {"question": "Which?", "recommended": "nope", "options": [
        {"id": "a", "label": "A", "attrs": {"Rate": "1%"}}, {"id": "b", "label": "B"}]})
    assert "attrs" not in v["options"][0] and "recommended" not in v          # one option only / unknown id
    v, _ = ask(guide, model, "r3", {"question": "Which?", "options": [
        {"id": "a", "label": "A", "description": "x", "attrs": {"K": "1"}},
        {"id": "b", "label": "B", "attrs": {"K": "2"}}]}, caps=["ask"])
    assert "description" not in v["options"][0] and "attrs" not in v["options"][0]   # the client cannot show them


def test_long_field_list_needs_search(guide, model):
    state = start(guide, LOAN)
    state["config"]["props"]["employer_industry"]["options"] = [{"id": f"i{i}", "name": f"Industry {i}"}
                                                                 for i in range(40)]
    v, _ = ask(guide, model, "r4", {"question": "Industry?", "field": "employer_industry",
                                    "suggested": ["i3", "zz", "i3"]}, state=state)
    assert v is not None and len(v["options"]) == 40 and v["suggested"] == ["i3"]
    v, _ = ask(guide, model, "r5", {"question": "Industry?", "field": "employer_industry"}, state=state,
               caps=["ask"])
    assert v is None and "too many options" in tool_result(model, "q1")       # no search in this client
    own = [{"id": f"o{i}", "label": f"O{i}"} for i in range(13)]
    v, _ = ask(guide, model, "r6", {"question": "Pick", "options": own}, state=state)
    assert v is None and "12 at most" in tool_result(model, "q1")              # the model's own list stays short


def test_number_range_from_the_field_and_address(guide, model):
    state = start(guide, LOAN)
    state["config"]["props"]["dependents_count"].update({"min": 0, "max": 10, "step": 1, "unit": "people"})
    v, _ = ask(guide, model, "r7", {"question": "How many?", "field": "dependents_count",
                                    "input": {"type": "number", "max": 4}}, state=state)
    assert v["input"] == {"type": "number", "min": 0, "max": 4, "step": 1, "unit": "people"}
    v, _ = ask(guide, model, "r8", {"question": "Your address?", "input": {"type": "address"}})
    assert v["input"] == {"type": "address"}
    v, _ = ask(guide, model, "r9", {"question": "Your address?", "input": {"type": "address"}}, caps=["ask"])
    assert v["input"] == {"type": "text"}


def test_several_fields_in_one_question(guide, model):
    q = {"question": "Your name?", "fields": [{"name": "first_name"}, {"name": "last_name", "required": True}]}
    v, state = ask(guide, model, "r10", q)
    assert [f["name"] for f in v["fields"]] == ["first_name", "last_name"] and v["options"] == []
    assert v["fields"][0]["label"] == "First name" and v["fields"][1]["required"] is True
    cfg = {**state["config"], "state": {**state["config"]["state"], "first_name": "Anna", "last_name": "Smith"}}
    model.script = [say("Thanks.")]
    collect(guide, "r10", resume={"answers": {"first_name": "Anna", "last_name": "Smith"}, "config": cfg})
    out = tool_result(model, "q1")
    assert "The user filled" in out and "first_name" in out and "Do not propose" in out

    v, _ = ask(guide, model, "r11", q, caps=["ask"])
    assert v is None and "one question at a time" in tool_result(model, "q1")
    v, _ = ask(guide, model, "r12", {"question": "?", "fields": [{"name": "first_name"}]})
    assert v is None and "2 to 3" in tool_result(model, "q1")


def test_a_typed_date_answer_fills_its_field(guide, model):
    v, state = ask(guide, model, "r13", {"question": "When were you born?", "field": "birth_date"})
    assert v["input"]["type"] == "date" and v["applies"] is True and v["label"] == "Date of birth"
    cfg = {**state["config"], "state": {**state["config"]["state"], "birth_date": "1990-03-12"}}
    model.script = [say("Thanks.")]
    collect(guide, "r13", resume={"answer": {"text": "1990-03-12"}, "config": cfg})
    assert "This filled the field Date of birth" in tool_result(model, "q1")
    q = next(e for e in guide.thread("r13")["transcript"] if e["kind"] == "question")
    assert q["applied"] is True


def test_a_typed_text_answer_fills_its_field(guide, model):
    # one tap: the answer fills the text field, no second "Fill in these fields?" card
    v, state = ask(guide, model, "r16", {"question": "Your first name?", "field": "first_name"})
    assert v["input"]["type"] == "text" and v["applies"] is True and v["label"] == "First name" and v["options"] == []
    cfg = {**state["config"], "state": {**state["config"]["state"], "first_name": "Anna"}}
    model.script = [say("Thanks.")]
    collect(guide, "r16", resume={"answer": {"text": "Anna"}, "config": cfg})
    out = tool_result(model, "q1")
    assert "The user wrote: Anna" in out and "This filled the field First name" in out and "do not propose it again" in out
    # without the config (the client did not fill it: the form refused it, or a question back) it is a plain answer
    v, _ = ask(guide, model, "r17", {"question": "Your first name?", "field": "first_name"})
    model.script = [say("Ok.")]
    collect(guide, "r17", resume={"answer": {"text": "why do you need it?"}})
    out = tool_result(model, "q1")
    assert "The user wrote: why do you need it?" in out and "This filled" not in out


def test_a_yes_no_question_fills_a_checkbox_field(guide, model):
    v, state = ask(guide, model, "r14", {"question": "Messaging apps fine?", "field": "contact_messenger",
                                         "options": ["Sure", "Rather not"]})
    assert [(o["id"], o["label"], o["value"]) for o in v["options"]] == [("yes", "Sure", True), ("no", "Rather not", False)]
    assert v["applies"] is True and v["multiple"] is False
    cfg = {**state["config"], "state": {**state["config"]["state"], "contact_messenger": True}}
    model.script = [say("Noted.")]
    collect(guide, "r14", resume={"answer": {"ids": ["yes"]}, "config": cfg})
    assert "This filled the field" in tool_result(model, "q1")
    v, _ = ask(guide, model, "r15", {"question": "Messaging apps fine?", "field": "contact_messenger"})
    assert [o["label"] for o in v["options"]] == ["Yes", "No"]
