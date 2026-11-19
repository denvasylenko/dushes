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
    # a reload shows it again in its place: an AG-UI activity message between the words
    msgs = guide.thread_messages("k2")
    kinds = [(m["role"], m.get("activityType")) for m in msgs if m["role"] in ("activity", "user") or m.get("content")]
    assert ("activity", "card") in kinds
    restored = next(m for m in msgs if m["role"] == "activity")
    assert restored["activity"]["blocks"][0]["items"][0]["value"] == "Arbat 12"


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


def test_a_hosts_own_block_passes_with_its_props_as_data():
    """The owner (2026-11-19): his own component as a block in any card. A card spec may hold a block type that is
    not built in when it is named with a hyphen; its keys reach the widget as they are, placeholders filled. A
    name without a hyphen that is no built-in is still a mistake."""
    spec = parse_cards([{
        "type": "pick_city", "description": "Ask which city.", "data": {"country": "string", "cities": "object[]"},
        "blocks": [{"type": "title", "text": "Which city in {country}?"},
                   {"type": "city-search", "name": "city", "placeholder": "Type a city", "options": "{cities}", "limit": 8},
                   {"type": "buttons", "items": [{"id": "ok", "label": "Use it", "style": "primary"}]}]}])[0]
    card = build(spec, {"country": "Portugal", "cities": [{"id": "lis", "label": "Lisbon"}]})
    assert card["blocks"][1] == {"type": "city-search", "name": "city", "placeholder": "Type a city",
                                 "options": [{"id": "lis", "label": "Lisbon"}], "limit": 8}
    for wrong in ("feild", "City-Search", "-search", "search-", "a" * 30 + "-" + "b" * 30):
        with pytest.raises(ValueError, match="unknown block"):
            parse_cards([{**BARBER, "blocks": [{"type": wrong}]}])


def test_a_search_block_in_a_card_spec():
    """The owner (2026-11-19): an input with search, options appearing as the person types, is a built-in block. The
    spec passes its options (from the model's data) or the name of a list the page serves."""
    spec = parse_cards([{
        "type": "pick_supplier", "description": "Ask which supplier.", "data": {"suppliers": "object[]"},
        "blocks": [{"type": "search", "name": "supplier", "label": "Supplier", "placeholder": "Type a name",
                    "options": "{suppliers}", "required": True},
                   {"type": "search", "name": "city", "source": "cities"},
                   {"type": "buttons", "items": [{"id": "ok", "label": "Choose", "style": "primary"}]}]}])[0]
    card = build(spec, {"suppliers": [{"id": "s1", "label": "Northwind", "description": "Paper"}]})
    assert card["blocks"][0]["options"] == [{"id": "s1", "label": "Northwind", "description": "Paper"}]
    assert card["blocks"][1] == {"type": "search", "name": "city", "source": "cities"}
