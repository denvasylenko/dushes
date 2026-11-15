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
