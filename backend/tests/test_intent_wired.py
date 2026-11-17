"""The choice layer wired into Dushes' run (demo branch): a move, a part of the page, a value, and the agent."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from formguide import intent
from formguide.site import Dushes, SiteMap

from .conftest import say
from .test_agent import start
from .test_questions import LOAN

SITE = Path(__file__).resolve().parents[1] / "demo" / "site.yaml"


class Mock:
    """Answers every question at once, as the external chooser does; records what it was sent."""
    by = "external"

    def __init__(self, **answers):
        self.answers, self.seen = answers, []

    async def choose_many(self, phrase, language, questions, screen):
        self.seen.append((phrase, questions, screen))
        return {name: intent.Pick(*self.answers[name]) for name in questions if name in self.answers}


def site_with(guide, chooser):
    s = Dushes(guide, SiteMap.load(SITE))
    s.intent = intent.Layer(intent.Settings(provider="jev", threshold=0.8, timeout_ms=200), chooser)
    return s


def run(site, thread, **kw):
    async def go():
        return [e async for e in site.run(thread, **kw)]
    return asyncio.run(go())


def directives(ev):
    return [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "site_directive"]


def text(ev):
    return "".join(e.get("delta", "") for e in ev if e.get("type") == "TEXT_MESSAGE_CONTENT")


def test_a_command_to_go_is_carried_out_without_the_agent(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_LABELS", "1")
    chooser = Mock(is_command=("yes", 0.98), kind=("navigate", 0.97), section=("/loans", 0.93))
    site = site_with(guide, chooser)
    before = len(model.calls)
    ev = run(site, "w1", message="open the loans page", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
    assert "Loans." in text(ev) and "Jev ·" in text(ev) and " ms" in text(ev)       # the label of who handled it
    assert ev[0]["type"] == "RUN_STARTED" and ev[-1]["type"] == "RUN_FINISHED"
    # only the phrase, the screen and the labels went out
    phrase, questions, screen = chooser.seen[0]
    assert phrase == "open the loans page" and screen == "/" and "Loans" in {o.label for o in questions["section"].options}


def test_a_question_or_an_unsure_pick_goes_to_the_agent(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_LABELS", "1")
    for answers in (dict(is_command=("no", 0.95), kind=("other", 0.9)),                          # not a command
                    dict(is_command=("yes", 0.95), kind=("navigate", 0.9), section=("/loans", 0.4)),   # not sure where
                    dict(is_command=("yes", 0.5), kind=("navigate", 0.9), section=("/loans", 0.9)),    # not sure it is one
                    dict(is_command=("yes", 0.95), kind=("other", 0.9))):
        site = site_with(guide, Mock(**answers))
        model.script = [say("The car loan starts from 18.9% a year.")]
        ev = run(site, f"w2-{len(model.calls)}", message="what does a car loan cost?", state={"page": {"path": "/"}})
        assert directives(ev) == [] and "18.9%" in text(ev) and "Haiku" not in text(ev).split("18.9%")[0]
        assert "— " in text(ev) and "not sure" in text(ev)                                  # the agent's label


def test_a_part_of_this_page_is_shown(guide, model):
    m = SiteMap.load(SITE)
    page = next(p for p in m.pages if p.parts)
    part = page.parts[0]
    chooser = Mock(is_command=("yes", 0.98), kind=("show", 0.95), element=(part.id, 0.9))
    ev = run(site_with(guide, chooser), "w3", message=f"show me {part.title}", state={"page": {"path": page.path}})
    d = directives(ev)
    assert len(d) == 1 and d[0]["path"] == page.path and part.id in d[0].values()


def test_a_value_named_outright_goes_through_the_forms_own_card_with_no_model_call(guide, model):
    state = {"page": {"path": "/apply"}, "form": start(guide, LOAN)}
    chooser = Mock(is_command=("yes", 0.98), kind=("explicit_value", 0.95), value=("loan_type=auto", 0.92))
    site = site_with(guide, chooser)
    before = len(model.calls)
    ev = run(site, "w4", message="choose car loan", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert card["changes"][0]["name"] == "loan_type" and card.get("quiet") is True       # applied at once, with Undo
    assert len(model.calls) == before                                                    # the agent's model was not asked
    labels = {o.label for o in chooser.seen[0][1]["value"].options}
    assert any(label.endswith(": Car loan") for label in labels)
    # a consent is never an option, so it can never be picked
    assert not any("consent" in o.id for o in chooser.seen[0][1]["value"].options)


def test_with_the_layer_off_nothing_changes(guide, model):
    site = Dushes(guide, SiteMap.load(SITE))
    assert not site.intent.on
    model.script = [say("", ("n1", "navigate", {"path": "/loans"})), say("Here is Loans.")]
    ev = run(site, "w5", message="open the loans page", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and "— " not in text(ev)
