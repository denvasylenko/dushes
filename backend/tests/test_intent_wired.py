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
    s.intent = intent.Layer(intent.Settings(provider="jev", threshold=0.5, timeout_ms=200), chooser)
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
    chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), section=("/loans", 0.93))
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
                    dict(is_command=("yes", 0.95), kind=("go_to", 0.9), section=("/loans", 0.4)),   # not sure where
                    dict(is_command=("yes", 0.9), kind=("question", 0.9), section=("/loans", 0.9)),    # a question never jumps
                    dict(is_command=("yes", 0.9), kind=("go_to", 0.9), section=("/loans", 0.9), needs_agent=("yes", 0.7)),
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
    chooser = Mock(is_command=("yes", 0.98), kind=("set_value", 0.95), value=("loan_type=auto", 0.92))
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


def test_an_order_to_go_that_names_a_value_and_no_place_is_a_value(guide, model):
    """The QA Lead's fix from her fifth set: "choose car loan" may come as an order to go; with no place named and
    a value named, it is that value."""
    state = {"page": {"path": "/apply"}, "form": start(guide, LOAN)}
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.7), value=("loan_type=auto", 0.9), section=("/apply", 0.9))
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "w6", message="choose car loan", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert card["changes"][0]["name"] == "loan_type" and card.get("quiet") is True and len(model.calls) == before
    assert directives(ev) == []


def test_a_date_is_never_a_place_to_go_and_a_name_off_the_screen_is_the_agents(guide, model):
    """The CPO's two rules, in code: neither line is even put to the chooser."""
    assert intent.has_date("put Friday") and intent.has_date("mets vendredi") and intent.has_date("book 25.11")
    assert not intent.has_date("open the loans page") and not intent.has_date("set the loan type to Car loan")
    screen = ["Loans", "Apply for a loan", "Loan type: Car loan"]
    assert intent.names_off_screen("open the table of Giulia", screen) and intent.names_off_screen("call Aster Logistics", screen)
    assert not intent.names_off_screen("open the Loans page", screen) and not intent.names_off_screen("Set the loan type to Car loan", screen)
    chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), section=("/loans", 0.93))
    site = site_with(guide, chooser)
    for line in ("open Friday", "open the request of Giulia"):
        model.script = [say("I can help with that on the right page.")]
        ev = run(site, f"w7-{len(model.calls)}", message=line, state={"page": {"path": "/"}})
        assert directives(ev) == [] and not chooser.seen


def test_the_layer_hands_back_instead_of_claiming(guide, model):
    """The CPO's hand-back cases the wiring can show today (2026-11-17): the code acts by itself only when it is
    sure and the action can be undone; everything else is the agent's."""
    from langchain_core.messages import AIMessage, ToolMessage
    # 4, 6: a value the form or the server did not take: the closing line is not said, the agent explains
    for result in ("The user rejected the changes.", "The user confirmed; changes applied. \u26a0 Loan type: not accepted",
                   "propose_changes failed: the slot is taken"):
        intent.preset("hb-1", "loan_type", "auto", "Loan type", "Car loan")
        assert intent.preset_model("hb-1", [AIMessage(content="")]) is not None          # the first step: propose it
        intent._PRESETS["hb-1"].pop(0)
        assert intent.preset_model("hb-1", [ToolMessage(content=result, tool_call_id="x")]) is None
        assert not intent.has_preset("hb-1")
    intent.preset("hb-2", "loan_type", "auto", "Loan type", "Car loan")
    intent._PRESETS["hb-2"].pop(0)
    applied = ToolMessage(content="The user confirmed; changes applied.", tool_call_id="x")
    assert intent.preset_model("hb-2", [applied]) is not None                            # applied cleanly: one line
    intent.clear_preset("hb-2")
    # 5: two fields fit, or the chooser is not sure which value: one question from the agent, nothing written
    state = {"page": {"path": "/apply"}, "form": start(guide, LOAN)}
    unsure = Mock(is_command=("yes", 0.9), kind=("set_value", 0.9), value=("loan_type=auto", 0.3))
    model.script = [say("Do you mean the amount or the term?")]
    ev = run(site_with(guide, unsure), "hb-3", message="put 18", state=state)
    assert not [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt"]
    assert "amount or the term" in text(ev)
    # 2: an order with a question in it is the agent's turn. Today the agent answers and offers the page (a line
    # that ends in a question opens nothing); "open it, then answer" is specified and not built yet
    both = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), section=("/loans", 0.9), needs_agent=("yes", 0.8))
    before = len(model.calls)
    model.script = [say("The car loan is at 18.9% a year. Want me to open Loans?")]
    ev = run(site_with(guide, both), "hb-4", message="open the loans page, what is the rate?", state={"page": {"path": "/"}})
    assert "18.9%" in text(ev) and len(model.calls) == before + 1 and "Jev \u00b7" not in text(ev)
    # 1: a place that is not there is not "opened": the agent says so
    gone = Mock(is_command=("yes", 0.9), kind=("show", 0.9), element=("no-such-part", 0.9))
    model.script = [say("I could not find that part; the page has Services and prices.")]
    page = next(p for p in SiteMap.load(SITE).pages if p.parts)
    ev = run(site_with(guide, gone), "hb-5", message="show me the gift cards", state={"page": {"path": page.path}})
    assert directives(ev) == [] and "could not find" in text(ev)


def test_in_a_talking_conversation_the_heard_line_goes_through_the_layer_and_the_label_is_not_said(guide, model, monkeypatch):
    """The owner's demo with the talking mode: what was heard is an ordinary line, so the layer acts on it; the
    voice says the answer ("Loans.") and never the line about who handled it."""
    from formguide import voice
    from .test_voice import _talks

    async def go():
        talks, live, _ = _talks()
        voice.watch(talks)
        await talks.start("anna", "o", "talk-1")
        monkeypatch.setenv("INTENT_LABELS", "1")
        chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), section=("/loans", 0.93))
        site = site_with(guide, chooser)
        before = len(model.calls)
        ev = [e async for e in site.run("talk-1", message="open the loans page", state={"page": {"path": "/"}})]
        assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
        assert "Jev \u00b7" in text(ev)                              # the label is on the screen
        for e in ev:
            voice.seen("talk-1", e)
        await asyncio.sleep(0.05)
        said = [m["content"] for m in live.sent if m["type"] == "session.commentary.append"]
        assert said == ["Loans."]                                    # and only the answer is said
        voice.HOSTS.clear()
    asyncio.run(go())
