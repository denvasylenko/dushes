"""Cards from blocks (card-blocks): specs in the config become tools; the widget draws the blocks."""
from __future__ import annotations

import pytest

from demo.mock_forms import FORMS
from formguide import FormGuide, GuideConfig, Models
from formguide.cards import answer_text, build, parse_cards

from .conftest import ScriptedChatModel, say
from .test_agent import collect, start
from .test_questions import interrupt_value, tool_result

LOAN = FORMS["loan_application"]

BARBER = {
    "type": "barber_match",
    "description": "Ask whether the barber we found is the one the user means.",
    "data": {"name": "string", "shop": "string", "rating": "number?", "photo": "string?", "slots": "string[]?"},
    "blocks": [
        {"type": "title", "text": "Is this your barber?"},
        {"type": "place", "title": "{name}", "subtitle": "{shop}", "rating": "{rating}", "image": "{photo}"},
        {"type": "choice", "name": "slot", "options": "{slots}", "if": "slots"},
        {"type": "buttons", "items": [{"id": "yes", "label": "Yes, book {name}", "style": "primary"},
                                      {"id": "no", "label": "Another barber"}]},
    ],
}
ROUTE = {
    "type": "route", "wait": False, "description": "Show how to get to the barbershop.",
    "data": {"address": "string"},
    "blocks": [{"type": "links", "items": [{"kind": "route", "label": "Route", "value": "{address}"}]}],
}


def guide_with(tmp_path, *cards) -> tuple[FormGuide, ScriptedChatModel]:
    m = ScriptedChatModel()
    return FormGuide(GuideConfig(models=Models(agent=m), data_dir=tmp_path, cards=list(cards))), m


def test_specs_are_checked_when_the_config_loads():
    assert [c.tool for c in parse_cards([BARBER, ROUTE])] == ["show_barber_match", "show_route"]
    for bad, needle in [
        ({**BARBER, "type": "Barber Match"}, "snake_case"),
        ({**BARBER, "blocks": [{"type": "carousel"}]}, "unknown block"),
        ({**BARBER, "blocks": [{"type": "text", "text": "{nickname}"}]}, "not in data"),
        ({**BARBER, "data": {"name": "colour"}}, "type must be"),
        ({**BARBER, "description": ""}, "description is required"),
        ({**BARBER, "colour": "red"}, "unknown key"),
    ]:
        with pytest.raises(ValueError, match=needle):
            parse_cards([bad])
    with pytest.raises(ValueError, match="same type"):
        parse_cards([BARBER, BARBER])


def test_a_card_is_filled_from_the_data():
    spec = parse_cards([BARBER])[0]
    assert spec.schema()["required"] == ["name", "shop"]
    card = build(spec, {"name": "Maria", "shop": "Arbat 12", "rating": 4.9, "slots": ["16:30", "18:00"]})
    assert card["type"] == "blocks" and card["name"] == "barber_match"
    place = card["blocks"][1]
    assert place["title"] == "Maria" and place["rating"] == 4.9 and place["image"] == ""   # a whole placeholder keeps the number
    assert card["blocks"][2]["options"] == ["16:30", "18:00"]                              # ...and the list
    assert card["blocks"][3]["items"][0]["label"] == "Yes, book Maria"
    no_slots = build(spec, {"name": "Maria", "shop": "Arbat 12"})
    assert [b["type"] for b in no_slots["blocks"]] == ["title", "place", "buttons"]          # if: slots, empty: dropped
    with pytest.raises(ValueError, match="shop is required"):
        build(spec, {"name": "Maria"})
    with pytest.raises(ValueError, match="rating must be number"):
        build(spec, {"name": "Maria", "shop": "x", "rating": "high"})


def test_a_waiting_card_is_an_interrupt_and_its_answer_goes_back(tmp_path):
    guide, model = guide_with(tmp_path, BARBER)
    model.script = [say("", ("c1", "show_barber_match", {"name": "Maria", "shop": "Arbat 12", "rating": 4.9}))]
    ev = collect(guide, "k1", message="book me with my barber", state=start(guide, LOAN))
    v = interrupt_value(ev)
    assert v["type"] == "blocks" and v["name"] == "barber_match" and v["blocks"][1]["title"] == "Maria"
    assert guide.thread("k1")["pending_card"]["kind"] == "blocks"
    model.script = [say("Booked with Maria.")]
    collect(guide, "k1", resume={"action": "yes", "label": "Yes, book Maria", "values": {"slot": "16:30"}})
    out = tool_result(model, "c1")
    assert 'The user chose "Yes, book Maria" (yes)' in out and "slot = 16:30" in out
    entry = next(e for e in guide.thread("k1")["transcript"] if e["kind"] == "blocks")
    assert entry["status"] == "answered" and entry["answer"]["action"] == "yes"


def test_a_display_card_is_an_event_and_the_turn_goes_on(tmp_path):
    guide, model = guide_with(tmp_path, ROUTE)
    model.script = [say("", ("c1", "show_route", {"address": "Arbat 12"})), say("Here is the route.")]
    ev = collect(guide, "k2", message="how do I get there", state=start(guide, LOAN))
    card = next(e["value"] for e in ev if e.get("name") == "card")
    assert card["blocks"][0]["items"][0]["value"] == "Arbat 12"
    assert interrupt_value(ev) is None
    assert "shown to the user" in tool_result(model, "c1")


def test_only_clients_that_draw_blocks_get_the_card_tools(tmp_path):
    guide, model = guide_with(tmp_path, BARBER)
    model.script = [say("Hi.")]
    collect(guide, "k3", message="hi", state=start(guide, LOAN), capabilities=["ask", "confirm"])
    assert "show_barber_match" not in [t["function"]["name"] if isinstance(t, dict) else t.name for t in model.bound]
    model.script = [say("Hi.")]
    collect(guide, "k4", message="hi", state=start(guide, LOAN), capabilities=["ask", "blocks"])
    assert "show_barber_match" in [t["function"]["name"] if isinstance(t, dict) else t.name for t in model.bound]


LOAN_PICK = {
    "type": "loan_pick", "description": "Offer the loan type you would pick.",
    "data": {"loan": "string"},
    "blocks": [{"type": "title", "text": "A {loan}?"},
               {"type": "buttons", "items": [{"id": "yes", "label": "Yes", "style": "primary", "fills": {"loan_type": "{loan}"}},
                                             {"id": "no", "label": "No"}]}],
}


def test_a_button_fills_form_fields_in_one_tap(tmp_path):
    guide, model = guide_with(tmp_path, LOAN_PICK)
    state = start(guide, LOAN)
    model.script = [say("", ("c1", "show_loan_pick", {"loan": "Car loan"}))]
    v = interrupt_value(collect(guide, "k5", message="which loan?", state=state))
    yes = v["blocks"][1]["items"][0]
    assert yes["fills"]["loan_type"]["id"] == "auto"                       # checked and in the form's own format
    assert v["fill_meta"]["loan_type"]["label"] == "Loan type" and v["fill_meta"]["loan_type"]["previous"] is None
    assert "fills" not in v["blocks"][1]["items"][1]
    cfg = LOAN.compute({**state["config"]["state"], "loan_type": yes["fills"]["loan_type"]})
    model.script = [say("Set.")]
    collect(guide, "k5", resume={"action": "yes", "label": "Yes", "values": {}, "config": cfg})
    out = tool_result(model, "c1")
    assert 'chose "Yes" (yes)' in out and "This filled Loan type (loan_type)" in out and "do not propose" in out
    # a value the field does not take goes back to the model to fix
    model.script = [say("", ("c1", "show_loan_pick", {"loan": "boat"})), say("Hm.")]
    collect(guide, "k6", message="which loan?", state=start(guide, LOAN))
    assert "no option" in tool_result(model, "c1")


def test_a_closed_card_says_so():
    spec = parse_cards([BARBER])[0]
    assert "without answering" in answer_text(spec, {"accepted": False})
