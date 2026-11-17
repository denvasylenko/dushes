"""The choice layer in front of the agents (internal, D-29): the contract, the generated questions, the fallback."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from formguide import intent
from formguide.form.layout import LayoutIndex
from formguide.form.overlay import Overlay
from formguide.site import SiteMap

from .test_questions import LOAN

SITE = Path(__file__).resolve().parents[1] / "demo" / "site.yaml"


class Scripted:
    """A chooser that answers what the test tells it to, after a delay, and records what it was sent."""
    by = "external"

    def __init__(self, pick: intent.Pick | None = None, delay: float = 0.0, fails: bool = False):
        self.answer, self.delay, self.fails, self.seen = pick, delay, fails, []

    async def choose(self, phrase, language, question, screen):
        self.seen.append((phrase, language, question, screen))
        await asyncio.sleep(self.delay)
        if self.fails:
            raise RuntimeError("the chooser is down")
        return self.answer


def ask(layer, phrase, question, language="en", screen="/"):
    return asyncio.run(layer.pick(phrase, language, question, screen))


SCREENS = intent.Question("choice", "screen", "Which screen?", (
    intent.Option("/today", "Today"), intent.Option("/guests", "Requests"), intent.Option("/stats", "Statistics")),
    act="navigate")
ON = intent.Settings(provider="jev", threshold=0.9, timeout_ms=100)


def test_the_layer_is_off_by_default_and_a_provider_without_a_client_is_off_too():
    assert intent.Settings().provider == "off" and not intent.Layer().on
    assert ask(intent.Layer(), "open requests", SCREENS) is None
    for provider in ("jev", "haiku"):               # no client is written yet: the agent takes every turn
        assert intent.chooser_for(intent.Settings(provider=provider)) is None
        assert ask(intent.Layer(intent.Settings(provider=provider)), "open requests", SCREENS) is None
    with pytest.raises(ValueError):
        intent.Settings(provider="acme")


def test_a_confident_pick_in_time_is_returned_and_names_no_supplier():
    chooser = Scripted(intent.Pick("/guests", 0.97))
    got = ask(intent.Layer(ON, chooser), "open requests", SCREENS, screen="/today")
    assert got is not None and got.id == "/guests" and got.confidence == 0.97 and got.by == "external"
    phrase, language, question, screen = chooser.seen[0]
    assert (phrase, language, screen) == ("open requests", "en", "/today")
    assert [o.label for o in question.options] == ["Today", "Requests", "Statistics"]


def test_without_a_usable_pick_the_agent_takes_the_turn():
    layer = lambda **kw: intent.Layer(ON, Scripted(**kw))  # noqa: E731
    assert ask(layer(pick=intent.Pick("/guests", 0.6)), "open requests", SCREENS) is None        # not confident
    assert ask(layer(pick=intent.Pick(None, 0.99)), "open requests", SCREENS) is None            # no pick
    assert ask(layer(pick=intent.Pick("/admin", 0.99)), "open requests", SCREENS) is None        # an id it made up
    assert ask(layer(pick=intent.Pick("/guests", 0.99), delay=0.5), "open requests", SCREENS) is None   # late
    assert ask(layer(fails=True), "open requests", SCREENS) is None                               # down
    assert ask(layer(pick=intent.Pick("/guests", 0.99)), "   ", SCREENS) is None                 # nothing said


def test_the_layer_only_looks_and_makes_reversible_edits():
    with pytest.raises(ValueError):
        intent.Settings(provider="jev", acts=("navigate", "delete"))
    chooser = Scripted(intent.Pick("b1", 0.99))
    delete = intent.Question("choice", "booking", "Which booking to delete?", (intent.Option("b1", "20:00"),), act="delete")
    assert ask(intent.Layer(ON, chooser), "delete the eight o'clock booking", delete) is None and not chooser.seen
    only_look = intent.Settings(provider="jev", acts=("navigate", "show"))
    amount = intent.Question("noul", "field:high_chair", "On?", act="set_field")
    assert ask(intent.Layer(only_look, Scripted(intent.Pick("yes", 0.99))), "with a high chair", amount) is None


def test_a_guests_name_or_phone_never_reaches_a_chooser():
    chooser = Scripted(intent.Pick("r2", 0.99))
    layer = intent.Layer(intent.Settings(provider="jev", never_send=("Marta Bellini",)), chooser)
    # a phrase with a guest's name, a phone or an e-mail is not sent at all
    assert ask(layer, "open Marta Bellini's request", SCREENS) is None
    assert ask(layer, "call +39 333 123 4567", SCREENS) is None
    assert ask(layer, "write to anna@aster.example", SCREENS) is None
    assert not chooser.seen
    # an option with a private label is left out; a request is an option by its number and time, never by a name
    records = [{"id": "r1", "number": 41, "time": "19:30", "name": "Marta Bellini"},
               {"id": "r2", "number": 42, "time": "20:00", "name": "Luca Ferri", "phone": "+39 333 765 4321"}]
    q = intent.record_question(records)
    assert [o.label for o in q.options] == ["41 19:30", "42 20:00"]
    mixed = intent.Question("choice", "guest", "Who?", (intent.Option("a", "Marta Bellini"), intent.Option("b", "Table 4")), act="show")
    assert ask(layer, "the eight o'clock one", mixed) is None      # "r2" is not among the options that were sent
    assert [o.label for o in chooser.seen[-1][2].options] == ["Table 4"]


def test_questions_are_generated_from_the_form_and_the_site_map():
    site = SiteMap.load(SITE)
    screens = intent.screen_question(site)
    assert screens.kind == "choice" and screens.act == "navigate" and len(screens.options) == len(site.pages)
    assert {o.id for o in screens.options} == {p.path for p in site.pages}
    page = next(p for p in site.pages if p.parts)
    assert [o.id for o in intent.element_question(page).options] == [x.id for x in page.parts]

    overlay = Overlay(LayoutIndex(LOAN.jsx), LOAN.compute(None))
    by_field = {q.about: q for q in intent.form_questions(overlay)}
    loan_type = by_field["field:loan_type"]
    assert loan_type.kind == "choice" and loan_type.act == "set_field" and "auto" in {o.id for o in loan_type.options}
    assert all(len(q.options) <= intent.MAX_OPTIONS for q in by_field.values())
    assert "field:first_name" not in by_field                       # free text is the agent's
    assert intent.field_question("high_chair", "High chair", "bool").kind == "noul"
    date = intent.field_question("day", "Day", "date")
    assert [o.id for o in date.options][:3] == ["today", "tomorrow", "day_after"] and "friday" in {o.id for o in date.options}
    guests = intent.field_question("guests", "Guests", "number", low=1, high=20)
    assert [o.id for o in guests.options] == [str(n) for n in range(1, 21)]
    assert intent.field_question("amount", "Amount", "number", low=1, high=5_000_000) is None   # not a choice
    assert intent.field_question("note", "Note", "text") is None
    assert [o.id for o in intent.turn_question().options] == ["navigate", "open", "pick", "edit", "question", "free_text"]
    assert [o.id for o in intent.confirm_question().options] == ["yes", "no", "none"]
    text_field = intent.field_for_text_question(overlay)
    assert text_field is not None and "first_name" in {o.id for o in text_field.options}


def test_the_rules_chooser_is_for_tests_only():
    with pytest.raises(ValueError):
        intent.chooser_for(intent.Settings(provider="rules"))
    layer = intent.Layer(intent.Settings(provider="rules", testing=True))
    assert ask(layer, "open requests please", SCREENS).id == "/guests"
    assert ask(layer, "show me something", SCREENS) is None
    assert ask(layer, "yes please", intent.Question("noul", "field:high_chair", "On?", act="set_field")).id == "yes"


def test_a_month_or_a_weekday_is_not_a_name_off_the_screen():
    from formguide import intent
    assert not intent.names_off_screen("1st July 2014", ["Date of birth"])
    assert not intent.names_off_screen("book it for Friday", ["Book a visit"])
    assert intent.names_off_screen("the request from Anna", ["Requests"])


def test_the_filter_takes_numbers_out_and_leaves_an_outline_whole():
    from formguide import intent
    layer = intent.Layer(intent.Settings(provider="off"))
    assert intent.scrub(layer, "call +39 333 123 4567 or 030 1234567, id 12345678") == "call <filled> or <filled>, id <filled>"
    outline = "1.1.2 [Accordion a] req 0/3\n    1.1.3 [Accordion b] req 0/10\n      (+1 nested)\n    1.1.4 [Tab c] req 2/7"
    assert intent.scrub(layer, outline) == outline
    assert intent.scrub(layer, "born 2014-07-01") == "born <filled>"       # a date written in digits is a value: it stays in
