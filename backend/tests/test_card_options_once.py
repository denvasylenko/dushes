"""A choice card shows its options; the words before it do not list them again."""
from __future__ import annotations

from formguide.agent.graph import without_options

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value

SERVICES = ["Haircut", "Beard trim", "Haircut + beard", "Kids haircut"]


def test_the_list_goes_and_the_rest_stays():
    text = ("A haircut takes 30 minutes on average.\n\nWhich service would you like?\n- Haircut\n- Beard trim\n"
            "- Haircut + beard\n- Kids haircut")
    assert without_options(text, SERVICES, "Pick one") == "Which service would you like?"   # the first line names one
    assert without_options("We are open until 8 pm. Here are the services:\n- Haircut\n- Beard trim",
                           SERVICES) == "We are open until 8 pm."
    assert without_options("Options are 10:00, 11:00 and 12:30. Which time suits you?",
                           ["10:00", "11:00", "12:30"]) == "Which time suits you?"
    assert without_options("Which time suits you?\n1. 10:00\n2. 11:00", ["10:00", "11:00"], "Which time suits you?") == ""


def test_text_that_names_fewer_than_two_options_is_untouched():
    for text in ("I would suggest the Haircut. Which service?", "Which service would you like?", ""):
        assert without_options(text, SERVICES) == text


def _run(guide, model, thread, lead):
    model.script = [say(lead, ("q1", "ask_user", {"question": "Which loan do you need?",
                                                  "options": ["Car loan", "Mortgage", "Cash loan"]}))]
    return collect(guide, thread, message="I need a loan", state=start(guide, LOAN))


def test_a_listed_lead_is_replaced_before_the_card(guide, model):
    ev = _run(guide, model, "o1", "You can choose between these:\n- Car loan\n- Mortgage\n- Cash loan\n"
                                  "It takes about five minutes to fill in.")
    retract = [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "text_retract"]
    assert len(retract) == 1
    texts: dict[str, str] = {}
    for e in ev:
        if e["type"] == "TEXT_MESSAGE_CONTENT":
            texts[e["messageId"]] = texts.get(e["messageId"], "") + e["delta"]
    kept = [t for mid, t in texts.items() if mid != retract[0]["value"]["messageId"]]
    assert kept == ["It takes about five minutes to fill in."]
    order = [e.get("name") or e["type"] for e in ev]
    assert order.index("text_retract") < order.index("on_interrupt")           # replaced before the card shows
    assert [o["label"] for o in interrupt_value(ev)["options"]] == ["Car loan", "Mortgage", "Cash loan"]
    shown = [e["text"] for e in guide.thread("o1")["transcript"] if e["kind"] == "assistant" and e.get("text")]
    assert shown == ["It takes about five minutes to fill in."]                 # a reload shows the same


def test_a_plain_lead_stays_as_written(guide, model):
    ev = _run(guide, model, "o2", "Happy to help with that.")
    assert not any(e.get("name") == "text_retract" for e in ev)
    assert "".join(e["delta"] for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT") == "Happy to help with that."
