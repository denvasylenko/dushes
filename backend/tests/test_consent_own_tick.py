"""A consent is given only by the person's own tick: never by "accept all", never by the agent."""
from __future__ import annotations

from types import SimpleNamespace

from formguide.agent.interaction import read_decision
from formguide.agent.tools import is_consent

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value, tool_result


def _is(label, props=None, role="bool", listed=False):
    ctx = SimpleNamespace(pack=SimpleNamespace(consents={"f": {}} if listed else {}))
    return is_consent(ctx, SimpleNamespace(role=role, name="f"), SimpleNamespace(label=label, props=props or {}))


def test_a_consent_is_known_by_its_label_the_pack_or_the_form():
    for label in ("I accept the rental terms", "I agree to a soft credit check", "Consent",
                  "The information I gave is true and complete", "I have read the privacy policy",
                  "Ich akzeptiere die AGB", "J'accepte les conditions", "Accetto i termini",
                  "\u042f \u0441\u043e\u0433\u043b\u0430\u0441\u0435\u043d \u0441 \u0443\u0441\u043b\u043e\u0432\u0438\u044f\u043c\u0438"):
        assert _is(label), label
    for label in ("Newsletter", "Pets in the household", "Contact me by messenger", "Automatic transmission"):
        assert not _is(label), label
    assert _is("Contact me by messenger", listed=True) and _is("Send me offers", {"consent": True})
    assert not _is("I accept the rental terms", {"consent": False})     # the form says it is not one
    assert not _is("I accept the rental terms", role="text")


def test_accept_all_never_gives_a_consent():
    changes = [{"name": "first_name"}, {"name": "terms", "consent": True}]
    assert read_decision(changes, {"accepted": True}) == (["first_name"], ["terms"])
    assert read_decision(changes, {"accepted": True, "names": ["first_name", "terms"]}) == (["first_name", "terms"], [])
    assert read_decision(changes, {"answer": {"text": "yes"}}) == (["first_name"], ["terms"])


def _propose(guide, model, thread, caps=None):
    state = start(guide, LOAN)
    state["config"]["props"]["contact_messenger"]["label"] = "I accept the rental terms"
    model.script = [say("", ("p1", "propose_changes", {"changes": [{"name": "contact_messenger", "value": True}]})),
                    say("Please tick it yourself.")]
    return collect(guide, thread, message="fill everything", state=state, capabilities=caps)


def test_a_terms_checkbox_becomes_an_unticked_consent_row(guide, model):
    v = interrupt_value(_propose(guide, model, "ct1"))
    assert v["changes"][0]["consent"] is True                      # the widget shows it unticked
    model.script = [say("The terms still need your tick.")]
    collect(guide, "ct1", resume={"accepted": True})               # "accept all" from a client or a typed yes
    out = tool_result(model, "p1")
    assert "Nothing was applied" in out and "Not ticked by the user: contact_messenger" in out


def test_without_a_row_to_tick_the_agent_cannot_set_it(guide, model):
    ev = _propose(guide, model, "ct2", caps=["ask"])
    assert interrupt_value(ev) is None                             # no card at all
    assert "is a consent: only the person gives it" in tool_result(model, "p1")


def test_a_question_about_a_consent_goes_with_its_field(guide, model):
    state = start(guide, LOAN)
    state["config"]["props"]["contact_messenger"]["label"] = "I agree to the cancellation policy"
    model.script = [say("", ("q1", "ask_user", {"question": "Before I send, do you agree to the cancellation policy?",
                                                "options": ["Yes", "No"]})),
                    say("", ("q2", "ask_user", {"field": "contact_messenger",
                                                "question": "Do you agree to the cancellation policy?"}))]
    v = interrupt_value(collect(guide, "ct3", message="send it", state=state))
    assert v["type"] == "ask" and v["field"] == "contact_messenger"       # the second, bound question is the card
    assert [o["id"] for o in v["options"]] == ["yes", "no"]
    assert v["consent"] is True and v["label"] == "I agree to the cancellation policy"   # its own text, to show
    first = tool_result(model, "q1")
    assert "asks for a consent" in first and "contact_messenger" in first

    model.script = [say("", ("q3", "ask_user", {"question": "Which day suits you?", "options": ["Mon", "Tue"]}))]
    v = interrupt_value(collect(guide, "ct4", message="book", state=state))
    assert v["type"] == "ask" and "field" not in v                         # an ordinary question is untouched
