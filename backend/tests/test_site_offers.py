"""The site agent answers a question first: a page opens and a form starts only on a direct request or a yes."""
from __future__ import annotations

from formguide.site.agent import wants_to_go

from .conftest import say
from .test_site import form_state, run, site  # noqa: F401 - the fixture


def test_a_question_is_not_a_request_to_go():
    for q in ("how can I get car insurance?", "what does a mortgage cost", "can I apply online?",
              "where are the contacts?", "how do I open an account?", "is the branch open on Saturday",
              "do you show prices anywhere?", "car insurance", "tell me about the sale",
              "can I book a table for fourteen people at Casa do Mar Azul?",          # asking whether, not ordering
              "Est-ce que je peux r\u00e9server une coupe pour samedi, comment \u00e7a marche ?",
              "wie kann ich einen Kredit bekommen?", "\u043a\u0430\u043a \u043e\u0444\u043e\u0440\u043c\u0438\u0442\u044c \u0441\u0442\u0440\u0430\u0445\u043e\u0432\u043a\u0443?"):
        assert not wants_to_go(q), q
    for q in ("open the contacts page", "show me the tariffs", "take me to pricing", "I want to apply",
              "I want a car loan of 900 000 for 3 years", "book me a haircut on Friday", "fill in the form for me",
              "can you open the insurance form?", "please show me the contacts", "Open Car insurance",
              "ich m\u00f6chte einen Kredit beantragen", "\u043e\u0442\u043a\u0440\u043e\u0439 \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u044b",
              "\u0445\u043e\u0447\u0443 \u043e\u0444\u043e\u0440\u043c\u0438\u0442\u044c \u0441\u0442\u0440\u0430\u0445\u043e\u0432\u043a\u0443"):
        assert wants_to_go(q), q
    assert wants_to_go("yes please", offered=True) and wants_to_go("ok", offered=True)
    assert not wants_to_go("yes please") and not wants_to_go("yes, but what does it cost?", offered=False)


def _events(ev, name):
    return [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == name]


def test_a_how_question_is_answered_and_the_form_is_offered(site, model):
    model.script = [say("", ("o1", "open_form", {"form_id": "loan_application", "note": "a car loan"})),
                    say("You apply online in about ten minutes. Want me to open the loan application?")]
    ev = run(site, "of1", message="how can I get a car loan?", state={"page": {"path": "/"}})
    assert _events(ev, "site_directive") == []                              # nothing opened
    result = next(m.content for m in model.calls[-1] if getattr(m, "tool_call_id", None) == "o1")
    assert result.startswith("Not opened: the person asked a question")
    taps = _events(ev, "suggestions")[0]["items"]
    assert taps[0].startswith("Open ") and wants_to_go(taps[0])              # the offer is one tap away
    assert "Want me to open" in "".join(e.get("delta", "") for e in ev)

    model.script = [say("", ("o2", "open_form", {"form_id": "loan_application", "note": "a car loan"})), say("Opening it.")]
    ev = run(site, "of1", message="yes please", state={"page": {"path": "/"}})   # a yes to the offer
    assert [d["form_id"] for d in _events(ev, "site_directive")] == ["loan_application"]


def test_a_yes_without_an_offer_opens_nothing(site, model):
    model.script = [say("", ("n1", "navigate", {"path": "/contacts"})), say("The contacts are on the Contacts page.")]
    ev = run(site, "of2", message="yes", state={"page": {"path": "/"}})
    assert _events(ev, "site_directive") == []


def test_a_where_question_gets_the_page_as_an_offer_and_the_tap_opens_it(site, model):
    model.script = [say("", ("n1", "navigate", {"path": "/contacts", "section": "bank"})),
                    say("The branch is open on Saturday 10:00 to 16:00. Want me to open Contacts?")]
    ev = run(site, "of3", message="when is the bank open on Saturday?", state={"page": {"path": "/"}})
    assert _events(ev, "site_directive") == []
    tap = _events(ev, "suggestions")[0]["items"][0]
    model.script = [say("", ("n2", "navigate", {"path": "/contacts", "section": "bank"})), say("Here is Contacts.")]
    ev = run(site, "of3", message=tap, state={"page": {"path": "/"}})        # the person tapped the offer
    assert _events(ev, "site_directive") == [{"type": "navigate", "path": "/contacts", "section": "bank"}]
