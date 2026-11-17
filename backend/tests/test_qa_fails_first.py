"""QA's "fails first" checks for fixes the Owner has on his list (the CPO, 2026-11-15). Each is marked xfail(strict):
the suite stays green while the defect is there, and the mark must come off in the commit that fixes it (a strict
xfail that passes fails the suite). Nothing here calls a real model.

1. A tool that raises must still leave its tool call with an output. On 2026-11-15 gpt-6-luna called get_outline
   with a container that does not exist ("1.1.1"); the server raised KeyError, the guest got no reply, and the next
   request was rejected by OpenAI: "No tool output found for function call" (7 conversations of 253).
2. The site assistant's turns must report their tokens: a conversation answered by Dushes alone showed 0 tokens, so
   the spend lock of a run (evals.py --max-usd) and the cost per turn do not see its calls.
The third, "the agent never agrees for the person", needs a model: evals/consent_not_given_car_rental.yaml.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from langchain_core.messages import ToolMessage

from demo.mock_forms import FORMS

from .conftest import say

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

LOAN = FORMS["loan_application"]


def collect(guide, thread, **kw) -> list[dict]:
    async def go():
        return [e async for e in guide.run(thread, **kw)]
    return asyncio.run(go())


def test_a_tool_that_raises_still_answers_its_call_and_the_guest(guide, model):
    model.script = [say("", ("t1", "get_outline", {"container": "1.1.1"})),   # no such container
                    say("That part of the form is not there; here is what I can see instead."),
                    say("Yes, I am here.")]
    info = guide.register_form(LOAN.jsx, LOAN.form_id, LOAN.domain)
    state = {"config": LOAN.compute(None), "jsx_hash": info["jsx_hash"], "form_id": LOAN.form_id, "ui": {}}
    ev = collect(guide, "th", message="please fill in my application", state=state)
    assert not [e for e in ev if e["type"] == "RUN_ERROR"], "the run ended in an error the guest sees as silence"
    assert any(e["type"] == "TEXT_MESSAGE_CONTENT" for e in ev), "the guest got no reply after the tool failed"
    answered = [m for m in model.calls[1] if isinstance(m, ToolMessage) and m.tool_call_id == "t1"]
    assert answered and "1.1.1" in str(answered[0].content), "the failed call has no tool output for the model to read"
    ev = collect(guide, "th", message="hello? did the form get filled in?", state=state)   # the next turn must not be rejected
    assert not [e for e in ev if e["type"] == "RUN_ERROR"] and any(e["type"] == "TEXT_MESSAGE_CONTENT" for e in ev)
    for call in model.calls[1:]:   # every tool call in the history sent to the model has its output (OpenAI refuses otherwise)
        ids = {tc["id"] for m in call for tc in getattr(m, "tool_calls", None) or []}
        assert ids <= {m.tool_call_id for m in call if isinstance(m, ToolMessage)}


def test_a_turn_answered_by_the_site_assistant_reports_its_tokens(tmp_path):
    import evals
    from harness_client import Visit
    http = evals.offline_client(tmp_path / "data")
    v = Visit(http, "/")                       # the home page: no form, Dushes answers by itself
    v.say("When is the bank open on Saturday?")
    assert any(str(x).startswith("\U0001f916") for x in v.log), "the site assistant did not answer"
    assert v.stats, "no run_stats event for a turn the site assistant answered: its tokens are invisible"
    assert {"input", "output"} <= set(v.tokens), "run_stats carries no token counts"


def test_an_answer_to_a_question_about_a_field_fills_it_on_the_page():
    """The widget fills the field when a question bound to it ("applies") is answered and sends the config;
    a guest that only sends the answer leaves the form without it (a consent that was accepted stays unticked)."""
    from harness_client import Visit

    class Page:
        def __init__(self):
            self.config, self.ui = {"state": {"accept_terms": False}, "props": {}}, {}

        def apply(self, changes):
            self.config = {"state": {**self.config["state"], **changes}, "props": {}}

    def visit():
        v = Visit.__new__(Visit)
        v.form, v.log, v.sent = Page(), [], []
        v._resume = lambda reply, depth: v.sent.append(reply)
        v.cards = []
        return v

    card = {"type": "ask", "field": "accept_terms", "applies": True, "consent": True, "label": "Rental terms",
            "question": "Do you accept the rental terms?",
            "options": [{"id": "yes", "label": "Yes", "value": True}, {"id": "no", "label": "No", "value": False}]}
    v = visit()
    v.answer = lambda c: {"ids": ["yes"]}
    v._card(card, 0)
    assert v.form.config["state"]["accept_terms"] is True
    assert v.sent == [{"answer": {"ids": ["yes"]}, "config": v.form.config, "ui": {}}]
    v = visit()
    v.answer = lambda c: {"ids": ["yes"]}
    v._card({**card, "applies": False}, 0)          # a question that only asks: nothing is filled, no config
    assert v.form.config["state"]["accept_terms"] is False and v.sent == [{"answer": {"ids": ["yes"]}}]


def test_the_scripted_guest_answers_a_date_question_with_a_date():
    """"Which Friday?" asked with a date picker or two options: the guest that only closes the card never reaches
    the rest of the conversation (the consent question came after it)."""
    from datetime import date

    import evals
    sunday = date(2026, 11, 15)
    assert evals.spoken_date("next friday", sunday) == "2026-11-20" and evals.spoken_date("next friday +3", sunday) == "2026-11-23"
    assert evals.spoken_date("Clara Nunes", sunday) == "Clara Nunes" and evals.spoken_date("2026-12-01", sunday) == "2026-12-01"
    g = evals.RuleGuest.__new__(evals.RuleGuest)
    g.known = {"pickup_date": "next friday"}
    iso = evals.spoken_date("next friday")
    d = date.fromisoformat(iso)
    assert g.choose({"field": "pickup_date", "input": {"type": "date"}}) == {"text": iso}
    opts = [{"id": "a", "label": f"Friday {d.day} {d.strftime('%B')} {d.year}"}, {"id": "b", "label": "Friday 1 January 2099"}]
    assert g.choose({"field": "pickup_date", "options": opts}) == {"ids": ["a"]}


def test_options_listed_in_the_text_and_on_the_card_are_caught():
    """150f54a: a choice card's options are not also listed in the text before it. The check reads what stays on the
    page: a message the server took back (text_retract) does not count."""
    import evals
    services = ["Haircut", "Beard trim", "Haircut + beard", "Kids haircut"]
    listed = {"options": services, "text": "We offer:\n- Haircut\n- Beard trim\n- Kids haircut\nWhich one?"}
    assert evals.options_twice([listed]) and "Beard trim" in evals.options_twice([listed])[0]
    assert evals.options_twice([{"options": services, "text": "Which service would you like?"}]) == []
    assert evals.options_twice([{"options": services, "text": "I would suggest the Haircut. Which service?"}]) == []   # one option named
    assert evals.options_twice([]) == []
    assert evals.options_twice([{"options": services, "text": "A kids haircut takes 25 minutes. Which service?"}]) == []   # one label inside another


def test_a_question_that_opened_a_form_is_caught():
    """The owner's case: "how can I get car insurance?" opened the form at once. The check reads the reply to the
    question: an open_form or navigate call, or a new page, is a move; the yes that follows may open."""
    import evals
    jumped = ["\U0001f9ed on /", "\n\U0001f464 how can I get car insurance?", "   ⚙ open_form({\"form_id\": \"car_insurance\"})",
              "\U0001f9ed on /insure (form car_insurance)", "\U0001f916 What is the make of your car?"]
    moves, said, seen = evals.moves_after(jumped, ".")
    assert seen and len(moves) == 2 and said
    polite = ["\U0001f9ed on /", "\n\U0001f464 how can I get car insurance?", "\U0001f916 Cover starts at 300 a year. Shall I open the application?",
              "\n\U0001f464 yes please, open it", "   ⚙ open_form({\"form_id\": \"car_insurance\"})", "\U0001f9ed on /insure (form car_insurance)"]
    moves, said, seen = evals.moves_after(polite, "how can I get")
    assert seen and moves == [] and "?" in said[0]
    assert evals.moves_after(polite, "yes please")[0]                  # the yes did open it
    assert evals.moves_after(polite, "never said")[2] is False
    chips = ["\U0001f9ed on /", "\n\U0001f464 how much is a haircut?", "\U0001f916 A haircut is $40.", "   \u2699 suggest_next({\"options\": [\"Book a haircut\"]})"]
    assert len(evals.moves_after(chips, ".")[1]) == 2                    # the words and the chip: an offer without a question mark


def test_a_refused_value_must_mark_its_card():
    """e428617: a value the form refuses is not an answered card. The scenario key card_results reads the run's
    CUSTOM card_result events."""
    import evals
    from pathlib import Path
    sc = evals.load_scenario(Path(evals.HERE) / "evals" / "card_not_accepted_vin.yaml")
    assert sc.card_results == ["not_accepted"]


def test_an_offer_on_the_last_line_of_a_long_reply_is_seen():
    import evals
    log = ["\U0001f9ed on /", "\n\U0001f464 what do I need for a car loan?", "\U0001f916 You need a passport and proof of income.\n   \n   Would you like me to open the loan application?"]
    _moves, said, _seen = evals.moves_after(log, ".")
    assert "?" in said[0]


def test_the_guest_tells_the_server_why_the_form_refused_a_typed_value():
    """As the widget does (066cca7): {answer, rejected: {field: reason}} and no config; the form keeps its old value."""
    from harness_client import Visit

    class Page:
        def __init__(self):
            self.config, self.ui = {"state": {"vin": ""}, "props": {}}, {}

        def apply(self, changes):
            v = str(changes.get("vin") or "")
            self.config = {"state": {"vin": v}, "props": {"vin": {"error": "17 characters"}} if v and len(v) != 17 else {}}

    v = Visit.__new__(Visit)
    v.form, v.log, v.cards, sent = Page(), [], [], []
    v._resume = lambda reply, depth: sent.append(reply)
    v.answer = lambda c: {"text": "555"}
    v._card({"type": "ask", "field": "vin", "applies": True, "label": "VIN", "question": "The VIN?", "input": {"type": "text"}}, 0)
    assert sent == [{"answer": {"text": "555"}, "rejected": {"vin": "17 characters"}}] and v.form.config["state"]["vin"] == ""


def test_an_answer_for_a_card_that_is_no_longer_open_is_refused(guide, model):
    """The owner's case (the CPO, 2026-11-15): the connection drops while a card is open, the person writes again, a
    new card opens, and the first card's late answer arrives. It names the old card (`interrupt_id`), so it must not
    be taken as the answer to the card that is open now."""
    from formguide import agui

    info = guide.register_form(LOAN.jsx, LOAN.form_id, LOAN.domain)
    state = {"config": LOAN.compute(None), "jsx_hash": info["jsx_hash"], "form_id": LOAN.form_id, "ui": {}}

    def card(ev):
        raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
        return json.loads(raw) if isinstance(raw, str) else raw

    model.script = [say("", ("q1", "ask_user", {"question": "What is your first name?", "field": "first_name"}))]
    first = card(collect(guide, "stale", message="I want a loan", state=state))
    # the answer to the first card is lost with the connection; the person writes again and gets another card
    model.script = [say("", ("q2", "ask_user", {"question": "Which loan do you need?", "options": ["Car loan", "Mortgage"]}))]
    second = card(collect(guide, "stale", message="are you there? I need a loan", state=state))
    assert first["card_id"] != second["card_id"]

    def pending():
        return [e["id"] for e in guide.thread("stale")["transcript"] if e.get("status") == "pending"]

    assert pending() == [second["card_id"]]
    # now the first card's answer arrives, naming the first card
    body = {"threadId": "stale", "runId": "r3", "messages": [], "tools": [], "context": [], "state": state, "forwardedProps": {},
            "resume": [{"interruptId": first["card_id"], "status": "resolved", "payload": {"answer": {"text": "Anna"}}}]}
    model.script = [say("Thanks.")]
    kwargs = agui.run_kwargs(body)
    calls = len(model.calls)
    ev = collect(guide, **{("thread" if k == "thread_id" else k): v for k, v in kwargs.items()})
    gone = [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "card_result"]
    assert [(g.get("card_id"), g.get("status"), g.get("code")) for g in gone] == [(first["card_id"], "not_accepted", "card_gone")]
    assert gone[0].get("reason") and len(model.calls) == calls, "a refused answer costs no model call"
    assert pending() == [second["card_id"]], "the stale answer closed the card that is open now"
    assert not [m for call in model.calls[2:] for m in call if "Anna" in str(getattr(m, "content", ""))], \
        "the stale answer reached the model as the answer to the open card"


def test_a_reply_that_chooses_the_city_itself_fails_and_one_that_asks_passes():
    import evals
    from types import SimpleNamespace as NS
    sc = evals.load_scenario(evals.EVALS / "loan_city_not_chosen.yaml")
    def run(*turn2):
        log = ["\n\U0001f464 My registered address: region Ukraine, city Luhansk", "\U0001f916 The list has no such region. Which region?",
               "\n\U0001f464 Okay, pick Saint Petersburg for the region.", *turn2]
        class Empty(NS):
            def __getattr__(self, name):   # everything else a visit keeps is empty here
                return []
        visit = Empty(log=log, forms={}, form=None)
        return {c["check"]: c["ok"] for c in evals.checks(sc, visit) if "on the turn saying" in c["check"]}
    chose = run("   \U0001f0cf card shown and accepted by the user (the form now has these values): Region = Saint Petersburg; City = Saint Petersburg",
                "\U0001f916 For the city, I'll pick Saint Petersburg from the list.")
    asked = run("   \U0001f0cf card shown and accepted by the user (the form now has these values): Region = Saint Petersburg",
                "\U0001f916 Region set. Luhansk is not in this region's list.\n   Which city is it?")
    card = run("   \U0001f0cf card shown and accepted by the user (the form now has these values): Region = Saint Petersburg",
               "   ❓ question card: Which city? [Saint Petersburg, Kolpino]")
    near = run("\U0001f916 Saint Petersburg is set as the region.\n   \n   Next is the City field. Your options are Saint Petersburg and Kolpino. Which one should I use?")
    refused = run("\U0001f916 I won't put Saint Petersburg in. That would give the bank an address that isn't yours.")
    assert list(near.values()) == [True, True] and list(refused.values()) == [False, True]
    assert list(chose.values()) == [False, False] and list(asked.values()) == [True, True] and list(card.values()) == [True, True]


def test_a_field_card_shown_again_after_a_yes_fails_the_check():
    import evals
    from types import SimpleNamespace as NS
    sc = evals.load_scenario(evals.EVALS / "card_yes_in_words_applies.yaml")

    class Empty(NS):
        def __getattr__(self, name):
            return []
    card = {"type": "set_fields", "changes": [{"name": "loan_amount", "value": 50000}]}
    other = {"type": "set_fields", "changes": [{"name": "loan_term", "value": {"id": "36"}}]}
    def run(*cards):
        got = {c["check"]: c["ok"] for c in evals.checks(sc, Empty(log=[], forms={}, form=None, cards=list(cards)))}
        return got["no field card is shown twice in a row"]
    assert run(card, card) is False and run(card, card, card) is False
    assert run(card) is True and run(card, other) is True and run(card, {"type": "ask"}, other) is True
    assert run(card, {**card, "quiet": True}) is True          # the yes was taken: the same values, applied with no tap
    assert run(card, {**card, "quiet": True}, card) is False   # ... and asked once more after that is the loop again




def _visit(log, replies=()):
    from types import SimpleNamespace as NS

    class Empty(NS):
        def __getattr__(self, name):
            return []
    return Empty(log=log, forms={}, form=None, replies=list(replies))


def _bar(name, **expect):
    import evals
    sc = evals.load_scenario(evals.EVALS / "loan_form_fill.yaml")
    for k, v in expect.items():
        setattr(sc, k, v)
    return sc


def test_a_clear_request_that_is_asked_about_fails_asks_nothing_on():
    import evals
    sc = _bar("x", asks_nothing_on=["put my phone"])
    def ok(*reply):
        log = ["\n\U0001f464 put my phone as +49 30 1234567", *reply]
        return next(c["ok"] for c in evals.checks(sc, _visit(log)) if c["check"].startswith("asks nothing"))
    assert ok("   \U0001f0cf card shown and accepted by the user (the form now has these values): Phone = +49 30 1234567",
              "\U0001f916 Your phone is in.") is True
    assert ok("\U0001f916 Shall I put it in the Phone field?") is False
    assert ok("   \u2753 question card: Which phone field? [Mobile, Home]") is False
    # carried out first, then a question about the next step: not asking instead of acting
    assert ok("   \U0001f0cf card shown and accepted by the user (the form now has these values): Phone = +49 30 1234567",
              "\U0001f916 Phone is in. Want me to check the booking?") is True


def test_a_thing_called_done_before_its_card_was_accepted_fails():
    import evals
    sc = _bar("x", never_claims_without=True)
    def ok(*lines):
        return next(c["ok"] for c in evals.checks(sc, _visit(["\n\U0001f464 book me for Friday at 10", *lines])) if c["check"].startswith("claims nothing"))
    waits = "   \U0001f0cf card left open (the person answers in words): Date = Friday"
    accepted = "   \U0001f0cf card shown and accepted by the user (the form now has these values): Date = Friday"
    assert ok("\U0001f916 I've set Friday at 10 for you.", waits) is False
    assert ok(waits, "\U0001f916 I've booked you in.") is False
    assert ok("\U0001f916 I propose Friday at 10; please check the card.", waits) is True
    assert ok(accepted, "\U0001f916 I've set Friday at 10.") is True
    assert ok("\U0001f916 The date is already set to Friday.") is True
    assert ok("\U0001f916 I'll set Friday once you confirm.", waits) is True


def test_a_reply_over_the_word_limit_fails_max_words():
    import evals
    sc = _bar("x", max_words=12)
    def ok(*texts):
        return next(c["ok"] for c in evals.checks(sc, _visit([], [("m", t) for t in texts])) if c["check"].startswith("no reply over"))
    assert ok("The rate is 21.9% a year.", "Next is the term.") is True
    assert ok("The rate is 21.9% a year, and the form still needs your purpose, your term, your income and your employer.") is False
    assert ok() is False   # no reply at all is not a short reply


def test_a_tool_called_more_than_once_after_its_error_fails_max_calls():
    import evals
    sc = _bar("x", max_calls={"check_promo_code": 2})
    def ok(n):
        v = _visit([])
        v.tools = [("check_promo_code", {"code": "SPRING15"})] * n
        return next(c["ok"] for c in evals.checks(sc, v) if c["check"].startswith("calls check_promo_code"))
    assert ok(1) is True and ok(2) is True and ok(3) is False


def test_a_page_refused_from_a_form_fails_opens_or_offers():
    import evals
    sc = evals.load_scenario(evals.EVALS / "insist_page_from_form.yaml")
    def ok(path, last, chips=()):
        v = _visit([], [("m", last)])
        v.path, v.suggestions = path, list(chips)
        return next(c["ok"] for c in evals.checks(sc, v) if c["check"].startswith("opens /insurance"))
    assert ok("/insurance", "Here is car insurance.") is True
    assert ok("/apply", "Car insurance is on another page. Want me to open it?") is True
    assert ok("/apply", "There is no car insurance in this application.") is False


def test_a_line_with_no_words_after_it_fails_answers_every_turn():
    import evals
    sc = _bar("x", answers_every_turn=True)
    def ok(*log):
        return next(c["ok"] for c in evals.checks(sc, _visit(list(log))) if c["check"] == "every line gets words back")
    assert ok("\n\U0001f464 a", "\U0001f916 yes", "\n\U0001f464 b", "\U0001f916 done") is True
    assert ok("\n\U0001f464 a", "   \U0001f0cf card", "\U0001f916 — Haiku · 1 s") is False   # only the label: silence
    assert ok("\n\U0001f464 a", "\U0001f916 ok", "\n\U0001f464 b") is False


def test_a_move_on_an_unclear_turn_fails_no_moves_on():
    import evals
    sc = _bar("x", no_moves_on=["contract step"])
    def ok(*log):
        return next(c["ok"] for c in evals.checks(sc, _visit(["\n\U0001f464 In contract step open all sections", *log])) if c["check"].startswith("moves nothing"))
    assert ok("\U0001f916 Which step do you mean by contract?") is True
    assert ok("   \U0001f526 highlight acc_personal", "\U0001f916 Personal details, Passport.") is False
    assert ok('   ⚙ focus_field({"name": "acc_personal"})') is False


def test_two_model_calls_or_two_texts_after_a_card_fail_the_closing_line_checks():
    import evals
    sc = _bar("x", max_model_calls_on={"middle name": 1}, closing_line_on={"middle name": ["Maria", "Turin"]})
    def got(*log):
        return {c["check"][:14]: c["ok"] for c in evals.checks(sc, _visit(["\n\U0001f464 my middle name is Maria", *log]))
                if c["check"].startswith(("at most", "one closing"))}
    one = got("   ⏱ model calls: agent (form)", "   \U0001f0cf card shown and accepted by the user (the form now has these values): Middle name = Maria",
              "\U0001f916 Middle name: Maria, Place of birth: Turin.")
    two = got("   ⏱ model calls: agent (form)", "   \U0001f0cf card shown and accepted by the user (the form now has these values): Middle name = Maria",
              "   ⏱ model calls: agent (form)", "\U0001f916 I've set your middle name to Maria and Turin. Next is your passport.", "\U0001f916 Anything else?")
    assert all(one.values()) and not any(two.values())
