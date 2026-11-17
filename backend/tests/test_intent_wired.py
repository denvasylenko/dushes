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

    async def choose_many(self, phrase, language, questions, screen, context=None):
        self.context = context or {}
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
    chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), target=("screen:/loans", 0.93))
    site = site_with(guide, chooser)
    before = len(model.calls)
    ev = run(site, "w1", message="open the loans page", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
    # the chooser picked the target; the label names it with its time
    assert "Loans." in text(ev) and "Jev \u00b7" in text(ev) and " ms" in text(ev) and "in code" not in text(ev)
    assert ev[0]["type"] == "RUN_STARTED" and ev[-1]["type"] == "RUN_FINISHED"
    # what went out: the line, the screen, and the site as paths
    phrase, questions, screen = chooser.seen[0]
    labels = {o.label for o in questions["target"].options}
    assert phrase == "open the loans page" and screen == "/" and "Loans" in labels and "Loans \u203a Mortgage" in labels


def test_a_question_or_an_unsure_pick_goes_to_the_agent(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_LABELS", "1")
    # every line is put to the chooser (the owner: fillers and politeness are its job, not a list in code); what
    # it does not take as the person's order with a sure target is the agent's
    for answers in (dict(is_command=("no", 0.95), kind=("question", 0.9), target=("screen:/loans", 0.9)),   # a question
                    dict(is_command=("yes", 0.95), kind=("go_to", 0.9), target=("screen:/loans", 0.4)),      # not sure where
                    dict(is_command=("yes", 0.9), kind=("question", 0.9), target=("screen:/loans", 0.9)),    # a question never jumps
                    dict(is_command=("yes", 0.95), kind=("other", 0.9))):
        chooser = Mock(**answers)
        model.script = [say("The rates are in the Loans section.")]
        ev = run(site_with(guide, chooser), f"w2-{len(model.calls)}", message="what about the rates", state={"page": {"path": "/"}})
        assert directives(ev) == [] and "Loans section" in text(ev) and chooser.seen
        assert "\u2014 " in text(ev) and "not sure" in text(ev)                                  # the agent's label
    # a date in the line never moves the person, whatever the chooser picks
    chooser = Mock(is_command=("yes", 0.95), kind=("go_to", 0.9), target=("screen:/book", 0.95))
    model.script = [say("Which service do you want on Friday?")]
    assert directives(run(site_with(guide, chooser), "w2-d", message="open Friday", state={"page": {"path": "/"}})) == []


def test_a_part_of_this_page_is_shown(guide, model):
    m = SiteMap.load(SITE)
    page = next(p for p in m.pages if p.parts)
    part = page.parts[0]
    chooser = Mock(is_command=("yes", 0.98), kind=("show", 0.95), target=(f"part:{page.path}#{part.id}", 0.9))
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
    # a line that is only the value ("Loan type: Car loan") need not sound like a command: a very sure option is set
    bare = Mock(is_command=("no", 0.52), value=("loan_type=auto", 0.98), asks_more=("no", 0.9), asks_move=("no", 0.9))
    before = len(model.calls)
    ev = run(site_with(guide, bare), "w4b", message="Loan type: Car loan", state=state)
    assert [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt"] and len(model.calls) == before
    # nor when the line does not say the option (the chooser, holding the conversation, named an earlier value)
    model.script = [say("Noted.")]
    ev = run(site_with(guide, bare), "w4d", message="my first name is Anna", state=state)
    assert not [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt"]
    # but not when the line asks about it, or the option is only likely
    for answers in (dict(value=("loan_type=auto", 0.98), kind=("question", 0.8)), dict(value=("loan_type=auto", 0.7)),
                    dict(value=("loan_type=auto", 0.98), asks_more=("yes", 0.6))):
        model.script = [say("A car loan is for buying a car.")]
        ev = run(site_with(guide, Mock(**answers)), f"w4c-{len(model.calls)}", message="what is a car loan", state=state)
        assert not [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt"]


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
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.7), value=("loan_type=auto", 0.9), target=("screen:/apply", 0.9))
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "w6", message="choose car loan", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert card["changes"][0]["name"] == "loan_type" and card.get("quiet") is True and len(model.calls) == before
    assert directives(ev) == []


def test_a_date_is_never_a_place_to_go_and_a_name_off_the_screen_is_the_agents(guide, model):
    """The CPO's two rules, in code: a date moves nobody whatever the chooser picks (a weekday is not a name, so the
    line may be put to it); a name the screen does not show is not even put to the chooser."""
    assert intent.has_date("put Friday") and intent.has_date("mets vendredi") and intent.has_date("book 25.11")
    assert not intent.has_date("open the loans page") and not intent.has_date("set the loan type to Car loan")
    screen = ["Loans", "Apply for a loan", "Loan type: Car loan"]
    assert intent.names_off_screen("open the table of Giulia", screen) and intent.names_off_screen("call Aster Logistics", screen)
    assert not intent.names_off_screen("open the Loans page", screen) and not intent.names_off_screen("Set the loan type to Car loan", screen)
    chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), target=("screen:/loans", 0.93))
    site = site_with(guide, chooser)
    model.script = [say("I can help with that on the right page.")]
    ev = run(site, "w7-a", message="open Friday", state={"page": {"path": "/"}})
    assert directives(ev) == []                                            # a date moves nobody
    # a name the screen does not show never leaves the process: the chooser gets "<name>" in its place, and the
    # line always goes on to the agent, which has the name
    none = Mock(is_command=("yes", 0.9), kind=("other", 0.9))
    model.script = [say("Here is Giulia's request.")]
    ev = run(site_with(guide, none), "w7-b", message="open the request of Giulia", state={"page": {"path": "/"}})
    assert none.seen[0][0] == "open the request of <name>" and "Giulia's request" in text(ev)


def test_the_layer_hands_back_instead_of_claiming(guide, model):
    """The CPO's hand-back cases the wiring can show today (2026-11-17): the code acts by itself only when it is
    sure and the action can be undone; everything else is the agent's."""
    from langchain_core.messages import AIMessage, ToolMessage
    # 4, 6: a value the form or the server did not take: the closing line is not said, the agent explains
    for result in ("The user rejected the changes.", "The user confirmed; changes applied. \u26a0 Loan type: not accepted",
                   "propose_changes failed: the slot is taken"):
        intent.preset("hb-1", "loan_type", "auto", "Loan type", "Car loan")
        assert intent.preset_model("hb-1", [AIMessage(content="")]) is not None          # the first step: propose it
        intent._PRESETS["hb-1"]["script"].pop(0)
        assert intent.preset_model("hb-1", [ToolMessage(content=result, tool_call_id="x")]) is None
        assert not intent.has_preset("hb-1")
    intent.preset("hb-2", "loan_type", "auto", "Loan type", "Car loan")
    intent._PRESETS["hb-2"]["script"].pop(0)
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
    # 2: an order with a question in it: the page opens at once and the agent, told so, answers the question
    both = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), target=("screen:/loans", 0.9), asks_more=("yes", 0.8))
    before = len(model.calls)
    model.script = [say("The car loan is at 18.9% a year.")]
    ev = run(site_with(guide, both), "hb-4", message="open the loans page, what is the rate?", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and "18.9%" in text(ev) and len(model.calls) == before + 1
    # "the line asks more" below the bar is a plain order: no model
    plain = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), target=("screen:/loans", 0.9), asks_more=("yes", 0.6))
    before = len(model.calls)
    ev = run(site_with(guide, plain), "hb-4b", message="can you open the loans", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
    # 1: a place that is not there is not "opened": the agent says so
    gone = Mock(is_command=("yes", 0.9), kind=("show", 0.9), target=("part:/nowhere#no-such-part", 0.9))
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
        chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), target=("screen:/loans", 0.93))
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


def test_a_direct_command_by_voice_gets_one_short_line_and_no_let_me_check(guide, model, monkeypatch):
    """The owner's standard after Siri (2026-11-17): "Open Telegram" opens it and the voice says "done", nothing
    more. A direct command the layer carried out: the voice's own acknowledgement is cancelled before it comes,
    and exactly one short line is given to the voice."""
    from formguide import voice
    from .test_voice import _talks

    async def go():
        talks, live, _ = _talks()
        voice.watch(talks)
        await talks.start("anna", "o", "talk-2")
        events = talks.events("live_1")
        live.push(type="session.input_transcript.delta", delta="Open the loans page.")
        live.push(type="session.delegation.created", delegation={"id": "item_7", "type": "delegation", "target": "client"})
        heard = [await asyncio.wait_for(events.__anext__(), 1) for _ in range(2)][-1]
        assert heard["type"] == "heard"
        chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), target=("screen:/loans", 0.93))
        site = site_with(guide, chooser)
        before = len(model.calls)
        ev = [e async for e in site.run("talk-2", message=heard["text"], state={"page": {"path": "/"}})]
        for e in ev:
            voice.seen("talk-2", e)
        await asyncio.sleep(0.05)
        assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
        sent = [(m["type"], m.get("delegation_id"), m.get("content")) for m in live.sent
                if m["type"] in ("session.thinking.append", "session.commentary.append")]
        assert sent == [("session.thinking.append", "item_7", ""),          # the "let me check" is cancelled first
                        ("session.commentary.append", "item_7", "Loans.")]  # then one short line, and nothing else
        assert "say exactly those words and nothing else" in voice.INSTRUCTIONS
        voice.HOSTS.clear()
    asyncio.run(go())


def test_what_the_chooser_is_sure_of_is_done_and_the_rest_of_the_line_goes_to_the_agent(guide, model, monkeypatch):
    """The owner (2026-11-17): the chooser does all it can; when something is left of the line (a question, an
    explanation, a text to write) the agent answers that, told what was done already. The label shows both."""
    monkeypatch.setenv("INTENT_LABELS", "1")
    chooser = Mock(is_command=("yes", 0.9), kind=("question", 0.8), asks_move=("yes", 0.9), asks_more=("yes", 0.9),
                   target=("screen:/loans", 0.95))
    site = site_with(guide, chooser)
    model.script = [say("The car loan is the cheapest.")]
    before = len(model.calls)
    ev = run(site, "mix-1", message="open loans and tell me the cheapest one", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before + 1
    assert [e["type"] for e in ev].count("RUN_STARTED") == 1 and [e["type"] for e in ev].count("RUN_FINISHED") == 1
    said = text(ev)
    assert said.index("Loans.") < said.index("The car loan is the cheapest.")
    assert "Jev \u00b7" in said and ": opened Loans \u00b7 then " in said
    system = str(model.calls[-1][0].content)                               # the agent is told what was done
    assert 'Already done for this message' in system and '"Loans" was opened' in system
    asked = [m for m in model.calls[-1] if getattr(m, "type", "") == "human"]
    assert len(asked) == 1                                                 # the message once, not twice
    # nothing left over: no model, the chooser's label alone
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9),
                   target=("screen:/loans", 0.95))
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "mix-2", message="open loans", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before and "then" not in text(ev)
    # free text or an explanation with no sure order: nothing is applied, the agent's turn
    chooser = Mock(is_command=("yes", 0.9), kind=("other", 0.9), asks_move=("no", 0.9), asks_more=("yes", 0.9),
                   target=("screen:/loans", 0.95))
    model.script = [say("Here is a text.")]
    ev = run(site_with(guide, chooser), "mix-3", message="write that we are open till late", state={"page": {"path": "/"}})
    assert directives(ev) == [] and "Here is a text." in text(ev)


def test_a_bare_date_is_put_into_the_field_the_chooser_names(guide, model):
    """"1st July 2014" with Personal details open: the chooser says which date field, the date itself is read in
    code, and the form applies it with Undo; no model."""
    state = {"page": {"path": "/apply"}, "form": start(guide, LOAN)}
    chooser = Mock(is_command=("yes", 0.8), kind=("set_value", 0.8), date_field=("birth_date", 0.7))
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "date-1", message="1st July 2014", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert card["changes"][0]["name"] == "birth_date" and "2014-07-01" in json.dumps(card) and len(model.calls) == before
    assert "date_field" in chooser.seen[0][1]


OWNERS_LINE = ("Okay, loan term is uh, ten years uh, an extra life insurance, uh, yes and SMS notification yes. "
               "And payment method uh, with uh, card bank")


def loan_tab_on_screen(guide):
    """The loan form with the sections of the owner's four fields open, as on his screen."""
    form = start(guide, LOAN)
    form["config"] = LOAN.compute({"loan_type": {"id": "mortgage"}})              # the term opens once the loan type is chosen
    lay = guide.layout(form["jsx_hash"])
    tabs, opened = {}, set()
    for name in ("loan_term", "opt_life_insurance", "opt_sms", "payout_method"):
        for a in lay.ancestors(name):
            if a.role == "accordion":
                opened.add(a.name)
            if a.role == "tab":
                tabs[lay.nodes[a.name].parent] = a.name
    return {**form, "ui": {"activeTabs": tabs, "openAccordions": sorted(opened)}}


def test_several_values_in_one_line_are_set_together(guide, model, monkeypatch):
    """The owner's spoken line, word for word (2026-11-17): the term, two ticks and the payout method in one
    line. Each field on the screen gets its own question, so the chooser answers for each; all it is sure of go
    on one card of the form, applied with Undo, and no model is called."""
    monkeypatch.setenv("INTENT_LABELS", "1")
    state = {"page": {"path": "/apply"}, "form": loan_tab_on_screen(guide)}
    answers = {"is_command": ("yes", 0.7), "kind": ("set_value", 0.7), "asks_more": ("no", 0.9), "value": ("loan_term=120", 0.51),
               "f:loan_term": ("loan_term=120", 0.93), "f:opt_life_insurance": ("opt_life_insurance=true", 0.9),
               "f:opt_sms": ("opt_sms=true", 0.88), "f:payout_method": ("payout_method=card", 0.86),
               "f:loan_type": ("loan_type=auto", 0.55)}                    # not sure, and not said: left alone
    chooser = Mock(**answers)
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "many-1", message=OWNERS_LINE, state=state)
    asked = chooser.seen[0][1]
    assert {"f:loan_term", "f:opt_life_insurance", "f:opt_sms", "f:payout_method"} <= set(asked)
    assert not any("consent" in k for k in asked)                          # a consent is never asked about
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert {c["name"] for c in card["changes"]} == {"loan_term", "opt_life_insurance", "opt_sms", "payout_method"}
    assert card.get("quiet") is True and len(model.calls) == before
    assert "the step it chose before" not in text(ev)
    # the line asks more: the same card, and after it the form's own model goes on instead of a closing line
    from formguide import intent as _i
    more = Mock(**{**answers, "asks_more": ("yes", 0.9)})
    ev = run(site_with(guide, more), "many-2", message=OWNERS_LINE + " and what is the rate?", state=state)
    assert next(e for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    form_thread = "many-2-loan_application"
    assert not _i.has_preset(form_thread)                                  # nothing decided is left: the model answers next


def test_several_sections_in_one_line_are_all_opened(guide, model):
    """The owner's line, word for word (2026-11-17): four sections of the tab on the screen. Each section gets a
    yes / no, so the chooser answers for each; all it is sure of are opened by the form's own "show" step, and the
    reply names them. No model."""
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": ["acc_personal"]}}}
    chooser = Mock(**{"is_command": ("yes", 0.9), "kind": ("go_to", 0.9), "asks_move": ("yes", 0.9), "asks_more": ("no", 0.9),
                      "target": ("form:/apply:acc_passport", 0.6), "s:acc_passport": ("yes", 0.95), "s:acc_addresses": ("yes", 0.9),
                      "s:acc_contacts": ("yes", 0.92), "s:acc_education": ("yes", 0.88), "s:acc_personal": ("no", 0.9)})
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "sec-1", message="Okay, open passport addresses, contacts and education sections", state=state)
    shown = [e["value"].get("target") for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "ui_directive"
             and e["value"].get("type") == "focus"]
    assert shown == ["acc_passport", "acc_addresses", "acc_contacts", "acc_education"], [e for e in ev if e.get("type") == "CUSTOM"]
    assert "Passport, Addresses, Contacts, Education." in text(ev) and len(model.calls) == before


def test_a_value_and_a_name_in_one_line(guide, model):
    """"my first name <a name>, gender man": the name never leaves and is the form assistant's to write; the
    option is the chooser's. The card is applied at once and the form's own model goes on after it."""
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": ["acc_personal"]}}}
    chooser = Mock(**{"is_command": ("no", 0.6), "kind": ("set_value", 0.8), "asks_more": ("no", 0.6), "f:gender": ("gender=m", 0.95)})
    model.script = [say("I have also put Anna as the first name.")]
    ev = run(site_with(guide, chooser), "nm-1", message="my first name Anna Rossi, gender male", state=state)
    assert chooser.seen[0][0] == "my first name <name> <name>, gender male"
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert [c["name"] for c in card["changes"]] == ["gender"] and card.get("quiet") is True
    assert "Gender: Male." not in text(ev)                                 # no closing line: the model goes on


def test_a_date_and_a_place_in_one_line(guide, model):
    """The owner's spoken line (2026-11-17): "Uh. Lugansk, uh, 1st July '92". The date is the chooser's (a year
    of two digits is read), the place is a text for the form's assistant, which goes on after the card."""
    assert intent.date_in("Uh. Lugansk, uh, 1st July '92")[0] == "1992-07-01"
    assert intent.date_in("born July 1, 1992 in Rome")[0] == "1992-07-01" and intent.date_in("open the loans page")[0] is None
    assert intent.says_more(intent.date_in("Uh. Lugansk, uh, 1st July '92")[1]) and not intent.says_more(intent.date_in("uh, 1st July 1992")[1])
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": ["acc_personal"]}}}
    chooser = Mock(is_command=("no", 0.6), kind=("set_value", 0.8), date_field=("birth_date", 0.9))
    model.script = [say("And Lugansk as the place of birth.")]
    ev = run(site_with(guide, chooser), "dp-1", message="Uh. Lugansk, uh, 1st July '92", state=state)
    assert "Lugansk" not in chooser.seen[0][0] and "<name>" in chooser.seen[0][0]      # the place does not leave
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert [c["name"] for c in card["changes"]] == ["birth_date"] and "1992-07-01" in json.dumps(card) and card.get("quiet") is True
    assert not intent.has_preset("dp-1-loan_application")                               # the form's model goes on after the card


def test_two_ticks_and_an_option_said_in_everyday_words(guide, model):
    """The owner's barbershop line (2026-11-17): "hair wash and hair styling, and Alex". The ticks are labelled
    "Add hair wash (+$10, +15 min)": said as "hair wash", they still count. The page reports no open sections."""
    from .test_agent import BARBER
    form = start(guide, BARBER)
    form["config"] = BARBER.compute({"service": {"id": "haircut"}})
    chooser = Mock(**{"kind": ("set_value", 0.8), "asks_more": ("no", 0.9), "f:barber": ("barber=alex", 1.0),
                      "f:add_wash": ("add_wash=true", 1.0), "f:add_styling": ("add_styling=true", 1.0)})
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "bb-1", message="I want hair wash and hair styling, and Alex as the barber",
             state={"page": {"path": "/book"}, "form": form})
    assert {"f:barber", "f:add_wash", "f:add_styling"} <= set(chooser.seen[0][1])
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert {c["name"] for c in card["changes"]} == {"barber", "add_wash", "add_styling"} and len(model.calls) == before


def test_all_the_sections_of_a_tab_and_a_repeat_goes_to_the_agent(guide, model):
    """The owner's two spoken lines (2026-11-17). "All the sections in the applicant tab" is every section of that
    tab, not the tab. And the same request said again right after the layer answered it is a miss: the agent's."""
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": []}}}
    answers = {"is_command": ("yes", 0.9), "kind": ("go_to", 0.9), "asks_move": ("yes", 0.9), "asks_more": ("no", 0.9),
               "target": ("form:/apply:tab_applicant", 0.9), "all_sections": ("yes", 0.93), "all_of": ("this:tab_applicant", 0.9)}
    site = site_with(guide, Mock(**answers))
    before = len(model.calls)
    ev = run(site, "all-1", message="Okay, can you please open all of the sections in the applicant tab", state=state)
    shown = [e["value"].get("target") for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "ui_directive"]
    assert shown == ["acc_personal", "acc_passport", "acc_addresses", "acc_contacts", "acc_education"] and len(model.calls) == before
    assert "Personal details, Passport, Addresses, Contacts, Education." in text(ev)
    # said again: not the same answer once more; the agent's model is asked and the layer opens nothing
    model.script = [say("They are all open now; which one do you want to start with?")] * 3
    ev = run(site, "all-1", message="Yeah, but can you open all the sections in applicant tab", state=state)
    assert len(model.calls) > before and "Personal details, Passport, Addresses, Contacts, Education." not in text(ev)
    # a tab alone, asked twice, is the same miss
    tab = site_with(guide, Mock(**{**answers, "all_sections": ("no", 0.9)}))
    run(tab, "all-2", message="open the applicant tab", state=state)
    calls = len(model.calls)
    model.script = [say("The Applicant tab is open.")] * 3
    run(tab, "all-2", message="open the applicant tab", state=state)
    assert len(model.calls) > calls


def faq_page():
    return next(p for p in SiteMap.load(SITE).pages if len([x for x in p.parts if x.kind in ("accordion", "section")]) >= 2)


def test_all_the_sections_of_a_page_and_an_honest_result_for_the_agent(guide, model):
    """The owner (2026-11-17), on the FAQ: "open all sections" was answered "all five are open" with one open. The
    chooser now opens every part of the page; and the agent's own tool tells it that one call opens one part."""
    page = faq_page()
    parts = [x for x in page.parts if x.kind in ("accordion", "section")]
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9), all_sections=("yes", 0.92),
                   all_of=(f"this:{page.path}", 0.9))
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "faq-1", message="In frequently asked question open all sections", state={"page": {"path": page.path}})
    opened = [d.get("tab") or d.get("section") for d in directives(ev)]
    assert opened == [x.id for x in parts] and len(model.calls) == before
    from formguide.site import agent as site_agent
    first = parts[0]
    told, _ = site_agent.directive(SiteMap.load(SITE), {"path": page.path, ("tab" if first.kind == "accordion" else "section"): first.id})
    assert "Only this one part of the page was opened" in told and "every other part is as it was" in told


def test_several_sections_named_in_another_language(guide, model):
    """QA (2026-11-17): in Russian, French, Italian only the first section opened. The form's labels are English, so
    "the line itself says it" cannot be checked there; the chooser's yes for each section stands."""
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": []}}}
    answers = {"is_command": ("yes", 0.9), "kind": ("go_to", 0.9), "asks_move": ("yes", 0.9), "asks_more": ("no", 0.9),
               "s:acc_passport": ("yes", 0.9), "s:acc_addresses": ("yes", 0.88), "s:acc_contacts": ("yes", 0.91)}
    for n, line in enumerate(("\u043e\u0442\u043a\u0440\u043e\u0439 \u043f\u0430\u0441\u043f\u043e\u0440\u0442, \u0430\u0434\u0440\u0435\u0441\u0430 \u0438 \u043a\u043e\u043d\u0442\u0430\u043a\u0442\u044b",   # Russian: open passport, addresses and contacts
                              "ouvre le passeport, les adresses et les coordonn\u00e9es de contact")):
        ev = run(site_with(guide, Mock(**answers)), f"lang-{n}", message=line, state=state)
        shown = [e["value"].get("target") for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "ui_directive"]
        assert shown == ["acc_passport", "acc_addresses", "acc_contacts"], (line, shown)


def test_what_was_said_elsewhere_goes_with_a_move_by_the_layer(guide, model):
    """QA's finding (2026-11-17, details_carry_to_new_form): after the layer moved the person to a form's page,
    that form knew nothing of what they had said. The move now leaves a hand-over note with their recent lines,
    as the agent's own move does; an order the layer carried out is not one of them."""
    from formguide.transcript import new_entry
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9), target=("screen:/apply", 0.95))
    site = site_with(guide, chooser)
    tx = site.forms.transcripts
    tx.append("carry-1", new_entry("user", text="for the loan application, I'm Anna Berg, born 1st July '92", form_id="barber_booking"))
    tx.append("carry-1", new_entry("user", text="open the barbershop", layer=True))
    ev = run(site, "carry-1", message="Yeah, open it", state={"page": {"path": "/book"}})
    d = directives(ev)[0]
    assert d["path"] == "/apply" and d.get("form_id") == "loan_application"
    note = next(e for e in reversed(tx.list("carry-1")) if e["kind"] == "handoff")
    assert "Anna Berg" in note["note"] and "1st July" in note["note"] and "open the barbershop" not in note["note"]
    # nothing said before: a plain move, no hand-over run
    ev = run(site_with(guide, chooser), "carry-2", message="open apply for a loan", state={"page": {"path": "/"}})
    assert "form_id" not in directives(ev)[0]


def test_a_date_and_an_option_in_one_line_are_both_set(guide, model):
    """"I am a woman, born on 1st July '92": the date and the list option are both the chooser's, on one card."""
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": ["acc_personal"]}}}
    chooser = Mock(**{"kind": ("set_value", 0.8), "date_field": ("birth_date", 0.92), "f:gender": ("gender=f", 1.0)})
    model.script = [say("Done.")]
    ev = run(site_with(guide, chooser), "dg-1", message="I am a woman, born on 1st July '92", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert [c["name"] for c in card["changes"]] == ["birth_date", "gender"] and card.get("quiet") is True


def test_all_the_sections_of_a_place_the_layer_did_not_resolve_is_the_agents(guide, model):
    """QA (2026-11-17), the owner's line: "In contract step open all sections". The form has no step of that name;
    the layer must not open the tab on the screen instead. And the agent can open several parts in one call."""
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": []}}}
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9), all_sections=("yes", 0.95))   # whose sections: the chooser names none of the places
    model.script = [say("Which step do you mean by the contract step?")] * 3
    before = len(model.calls)
    ev = run(site_with(guide, chooser), "ctr-1", message="In contract step open all sections", state=state)
    assert not [e for e in ev if e.get("type") == "CUSTOM" and e.get("name") in ("ui_directive", "site_directive")]
    assert len(model.calls) > before
    from formguide.site import agent as site_agent
    page = faq_page()
    ids = [x.id for x in page.parts if x.kind in ("accordion", "section")]
    told, ds = site_agent.directives_for(SiteMap.load(SITE), {"path": page.path, "parts": ids + ["no-such"]})
    assert [d.get("tab") or d.get("section") for d in ds] == ids and "No such part: no-such" in told and f"{len(ids)} of its" in told


def test_the_decision_trace_of_a_turn(guide, model, monkeypatch):
    """A host that turns it on (INTENT_TRACE=1) gets CUSTOM decision_trace before the run ends: the line as it left
    the filter, every question with its answer (used or not), what was applied, and why the agent was brought in."""
    def trace(ev):
        return next((e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "decision_trace"), None)
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9), target=("screen:/loans", 0.95),
                   needs_agent=("no", 0.3))
    ev = run(site_with(guide, chooser), "tr-0", message="open loans", state={"page": {"path": "/"}})
    assert trace(ev) is None                                               # off unless the host asks
    monkeypatch.setenv("INTENT_TRACE", "1")
    ev = run(site_with(guide, chooser), "tr-1", message="open loans", state={"page": {"path": "/"}})
    t = trace(ev)
    assert t["outcome"] == "jev" and t["applied"] == [{"what": "open", "target": "/loans", "label": "Loans"}] and t["to_agent"] is None
    assert t["said"] == "open loans" and t["threshold"] == 0.5 and t["bars"]["tail"] == 0.7 and t["run_id"]
    stats = [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "run_stats"]
    assert len(stats) == 1 and stats[0]["run_id"] == t["run_id"] and stats[0]["models"] == []   # a turn with no model still shows
    by_about = {q["about"]: q for q in t["questions"]}
    assert by_about["target"]["answer"] == "screen:/loans" and by_about["target"]["answer_label"] == "Loans" and by_about["target"]["used"]
    assert by_about["needs_agent"]["used"] is False and by_about["needs_agent"]["p"] == 0.3     # asked, answered, not used
    # a phone in the line: the chooser is not asked at all, and what is shown back is masked
    model.script = [say("Noted.")]
    t = trace(run(site_with(guide, chooser), "tr-1b", message="open loans, my phone is +39 333 123 4567", state={"page": {"path": "/"}}))
    assert t["filtered"]["phones_or_digits"] == 1 and "333" not in json.dumps(t) and t["outcome"] == "agent"
    # a name is masked in what is shown back, and the turn goes on to the agent
    none = Mock(is_command=("yes", 0.9), kind=("other", 0.9))
    model.script = [say("Here it is.")]
    t = trace(run(site_with(guide, none), "tr-2", message="open the request of Giulia", state={"page": {"path": "/"}}))
    assert t["said"] == "open the request of <name>" and t["outcome"] == "agent" and t["to_agent"]["why"] == "name_masked"
    assert t["filtered"]["names"] == 1 and "Giulia" not in json.dumps(t)


def test_an_applied_card_ends_on_one_line_written_in_code(guide, model):
    """The CPO (2026-11-17), the owner's standard "done, one short line": the form assistant's own card, applied at
    once because the person said the values outright, is not followed by a second model call that only says so.
    The other side: when the form reacts with something to explain, the model speaks as before."""
    from .test_agent import collect
    assert intent.clean_result("The user confirmed; changes applied.\nCHANGES v1 \u2192 v2:\nagent (confirmed by user): first_name \u2205 \u2192 Anna")
    assert intent.clean_result("The user confirmed; changes applied.\nform reacted:\n  error fixed: birth_date\n  \u2298\u2192\u2713 became available loan_term")
    for bad in ('form reacted:\n  ! error birth_date: "must be 18 to 75"', "form reacted:\n  + appeared insurer", "form reacted:\n  * became required insurer",
                "The user applied: a. Declined (not applied): b."):
        assert not intent.clean_result("The user confirmed; changes applied.\n" + bad)
    state = start(guide, LOAN)
    model.script = [say("", ("p1", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]})), say("SECOND CALL")]
    ev = collect(guide, "one-1", message="my first name is Anna", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert card.get("quiet") is True
    calls = len(model.calls)
    cfg = LOAN.compute({**state["config"]["state"], "first_name": "Anna"})
    ev = collect(guide, "one-1", resume={"accepted": True, "config": cfg})
    assert "First name: Anna." in text(ev) and "SECOND CALL" not in text(ev) and len(model.calls) == calls
    # a line with a question in it: the model answers after the card, as before
    model.script = [say("", ("p2", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]})), say("It is Anna now; the rate is 18.9%.")]
    ev = collect(guide, "one-2", message="my first name is Anna, and what is the rate?", state=start(guide, LOAN))
    ev = collect(guide, "one-2", resume={"accepted": True, "config": cfg})
    assert "the rate is 18.9%" in text(ev)


def test_the_trace_names_a_form_section_and_a_code_line_is_not_a_model_call(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_TRACE", "1")
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": []}}}
    chooser = Mock(**{"is_command": ("yes", 0.9), "kind": ("go_to", 0.9), "asks_move": ("yes", 0.9), "asks_more": ("no", 0.9),
                      "s:acc_passport": ("yes", 0.95), "s:acc_addresses": ("yes", 0.9)})
    ev = run(site_with(guide, chooser), "trl-1", message="open passport and addresses", state=state)
    t = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "decision_trace")
    assert [a["label"] for a in t["applied"]] == ["Passport", "Addresses"] and "labels" not in t
    kinds = [m["kind"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "run_stats" for m in e["value"]["models"]]
    assert kinds and set(kinds) == {"code"}                                # the layer's steps: written in code, no model


def test_the_form_assistant_alone_opens_every_section_asked_for(guide, model):
    """The owner on the form demo (2026-11-17): "Open all sections" was answered "I can't open every section at once"
    twice, and done on the third asking. With no layer at all: one call a section in one step opens every one, and
    both the rule and the tool say that it can."""
    from .test_agent import collect
    from formguide.agent import prompts, tools
    names = ["acc_personal", "acc_passport", "acc_addresses", "acc_contacts", "acc_education"]
    model.script = [say("", *[(f"f{i}", "focus_field", {"name": n}) for i, n in enumerate(names)]),
                    say("Personal details, Passport, Addresses, Contacts and Education are open.")]
    ev = collect(guide, "all-form-1", message="Open all sections", state=start(guide, LOAN))
    shown = [e["value"].get("target") for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "ui_directive"]
    assert shown == names
    spec = next(t for t in tools.TOOLS if t["name"] == "focus_field") if hasattr(tools, "TOOLS") else None
    text = json.dumps(spec) if spec else open(tools.__file__).read()
    assert "once for each of them in the same step" in text and "Never say you cannot open several at once" in open(prompts.__file__).read()


def test_a_bare_name_of_a_place_opens_it_and_okay_is_not_a_name(guide, model, monkeypatch):
    """The owner's session (2026-11-17). "collateral", "purchase request": the name alone is enough when the chooser
    is sure of the place. And "Oh Okay, okay, okay. Open the apply for a loan" got a sentence from the model after
    the page opened, because "Okay" was taken for a person's name and such a line always goes on to the agent."""
    monkeypatch.setenv("INTENT_LABELS", "1")
    assert intent.mask_names("Oh Okay, okay, okay. Open the apply for a loan", []) == ("Oh Okay, okay, okay. Open the apply for a loan", False)
    assert intent.mask_names("Oh Okay, call Giulia", [])[1]
    bare = Mock(is_command=("no", 0.6), asks_move=("no", 0.6), asks_more=("no", 0.9), target=("screen:/loans", 0.85), was_offered=("yes", 0.85))
    before = len(model.calls)
    ev = run(site_with(guide, bare), "bare-1", message="loans", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
    assert "was_offered" in bare.seen[0][1]
    # the same word in a conversation about something else: the chooser does not see the wish to go there
    model.script = [say("Loans start from 18.9% a year.")]
    idle = Mock(is_command=("no", 0.6), asks_move=("no", 0.6), asks_more=("no", 0.9), target=("screen:/loans", 0.95), was_offered=("no", 0.8))
    assert directives(run(site_with(guide, idle), "bare-0", message="loans", state={"page": {"path": "/"}})) == []
    # a bare name that the conversation does not back, even when the chooser reads it as an order (QA's scenarios:
    # after a talk about prices, or as the first line): nothing opens, the agent answers and offers
    model.script = [say("The office is at 12 Main Street. Want me to open Contacts?")]
    order = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.8), asks_more=("no", 0.9), target=("screen:/loans", 0.95), was_offered=("no", 0.8))
    ev = run(site_with(guide, order), "bare-2", message="loans", state={"page": {"path": "/"}})
    assert directives(ev) == [] and "Main Street" in text(ev)
    # after a move the layer has just carried out, the next bare name is one more move
    chain = site_with(guide, Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9), target=("screen:/loans", 0.95)))
    run(chain, "bare-3", message="open loans", state={"page": {"path": "/"}})
    chain.intent.chooser.answers.update(target=("screen:/contacts", 0.9), was_offered=("no", 0.7), is_command=("no", 0.6), kind=("other", 0.5), asks_move=("no", 0.6))
    assert directives(run(chain, "bare-3", message="contacts", state={"page": {"path": "/loans"}})) == [{"type": "navigate", "path": "/contacts"}]
    assert intent.only_names("uh, the contacts", "Contacts") and not intent.only_names("open contacts", "Contacts")
    # a name with more said, or a question, is not a bare name: the usual rules hold
    for line in ("loans are expensive these days", "loans?"):
        model.script = [say("Here is what we have on loans.")]
        ev = run(site_with(guide, Mock(is_command=("no", 0.6), asks_move=("no", 0.6), asks_more=("no", 0.9), target=("screen:/loans", 0.85), was_offered=("yes", 0.9))),
                 f"bare-{len(model.calls)}", message=line, state={"page": {"path": "/"}})
        assert directives(ev) == [], line
    # "Okay" is no name: the page opens and no model adds a sentence
    ok = Mock(is_command=("yes", 0.9), kind=("go_to", 0.83), asks_move=("yes", 0.83), asks_more=("no", 0.72), target=("screen:/loans", 0.92))
    before = len(model.calls)
    ev = run(site_with(guide, ok), "ok-1", message="Oh Okay, okay, okay. Open the loans", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before and "then" not in text(ev)


def test_the_chooser_is_told_which_page_was_open_before(guide, model):
    """The QA Lead's probe (2026-11-17): after Barbershop then Contacts, "open the previous one" opened a part of
    Contacts with the old page's name; the chooser had no way to know where the person had been. The page open
    just before this one is now marked among the options, and the trail is in its state."""
    pages = [p for p in SiteMap.load(SITE).pages][:3]
    a, b = pages[1], pages[2]
    chooser = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), asks_more=("no", 0.9), target=(f"screen:{b.path}", 0.9))
    site = site_with(guide, chooser)
    run(site, "back-1", message=f"open {b.title}", state={"page": {"path": a.path}})
    chooser.answers["target"] = (f"screen:{a.path}", 0.9)
    ev = run(site, "back-1", message="open the previous one", state={"page": {"path": b.path}})
    options = {o.id: o for o in chooser.seen[-1][1]["target"].options}
    assert "just before this one" in options[f"screen:{a.path}"].hint
    assert not any("just before this one" in o.hint for i, o in options.items() if i != f"screen:{a.path}")
    assert chooser.context["pages_visited"] == [a.title, b.title]
    assert directives(ev) == [{"type": "navigate", "path": a.path}]


def test_a_question_about_another_page_asked_on_a_form_goes_to_the_site_assistant(guide, model):
    """QA (2026-11-17): "what I need for loan" on the booking form was refused by the form's assistant ("I can't
    help with a loan here"). The chooser says which page the line is about; when it is another page and the line
    is not an order, the site's assistant answers and nobody is moved."""
    from .test_agent import BARBER
    state = {"page": {"path": "/book"}, "form": start(guide, BARBER)}
    chooser = Mock(is_command=("no", 0.8), kind=("question", 0.9), asks_move=("no", 0.9), asks_more=("yes", 0.9), target=("screen:/loans", 0.8))
    model.script = [say("For a loan you need a passport and proof of income.")]
    ev = run(site_with(guide, chooser), "awa-1", message="Okay, what I need for loan", state=state)
    assert directives(ev) == [] and "passport" in text(ev)
    assert any(e.get("type") == "CUSTOM" and e.get("name") == "run_stats" and e["value"].get("agent") == "site" for e in ev)
    from formguide.agent import prompts
    from formguide.site import agent as site_agent
    assert "Answer what was asked" in open(prompts.__file__).read() and "Answer what was asked" in site_agent.SYSTEM


def test_a_date_without_its_year_and_the_year_said_after(guide, model):
    """The owner's session (2026-11-17), the QA Lead's two scenarios. "I was born on the 1st of July", then "1991":
    the date is whole and is filled at once, by the layer and by the form's assistant alike; and the question card
    for the year knows the day and the month already."""
    from formguide import voice
    from formguide.transcript import new_entry
    from .test_agent import collect
    assert intent.partial_date("I was born on the 1st of July") == (1, 7) and intent.partial_date("born July 1") == (1, 7)
    assert intent.partial_date("born 1st July 1991") is None and intent.partial_date("open the loans page") is None
    assert intent.bare_year("1991") == 1991 and intent.bare_year("uh, 1991.") == 1991 and intent.bare_year("in 1991 I moved") is None
    # the layer: the year completes the date said before
    state = {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": ["acc_personal"]}}}
    chooser = Mock(kind=("set_value", 0.8), date_field=("birth_date", 0.9))
    site = site_with(guide, chooser)
    site.forms.transcripts.append("yr-1", new_entry("user", text="I was born on the 1st of July", form_id="loan_application"))
    before = len(model.calls)
    ev = run(site, "yr-1", message="1991", state=state)
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    card = json.loads(raw) if isinstance(raw, str) else raw
    assert card["changes"][0]["name"] == "birth_date" and "1991-07-01" in json.dumps(card) and card.get("quiet") is True
    assert len(model.calls) == before
    # the form's assistant alone: its card for the whole date is applied at once, since both halves were said
    row = {"name": "birth_date", "label": "Date of birth", "value": "1991-07-01"}
    assert voice.said_outright({"type": "set_fields", "changes": [row]}, "1991", "I was born on the 1st of July")
    assert not voice.said_outright({"type": "set_fields", "changes": [row]}, "1991", "I was born in the summer")
    # the question card for a date knows the day and month already said
    model.script = [say("Which year were you born?", ("q1", "ask_user", {"question": "Which year were you born?", "field": "birth_date"}))]
    ev = collect(guide, "yr-2", message="I was born on the 1st of July", state=start(guide, LOAN))
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    ask = json.loads(raw) if isinstance(raw, str) else raw
    assert ask["input"]["type"] == "date" and ask["input"]["known"] == {"day": 1, "month": 7}


def test_a_missing_year_is_named_in_the_same_reply_before_any_tap(guide, model, monkeypatch):
    """The QA Lead's runs (2026-11-17, missing_year_named_at_once) and Head of Design's wording. When the person's
    line holds a day and a month with no year, the card of that turn carries no date and WAITS for them, a plain
    sentence names it before the card: "Date of birth: July 1. Which year?". No line when the card is applied at
    once (the year question card follows it straight away and asks), nor when the model said it itself."""
    from formguide import voice
    from .test_agent import collect
    assert intent.ask_the_year("Date of birth", 1, 7, "en") == "Date of birth: July 1. Which year?"
    assert intent.ask_the_year("Geburtsdatum", 1, 7, "de") == "Geburtsdatum: 1. Juli. Welches Jahr?"
    assert intent.ask_the_year("Fecha", 3, 2, "es").startswith("Fecha: 3 de febrero.") and "____" not in intent.ask_the_year("X", 1, 7, None)
    line = "my name is Anna Rossi, I was born 1st July and my gender is female"
    card = ("p1", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}, {"name": "last_name", "value": "Rossi"}]})
    said = lambda ev: "".join(e.get("delta", "") for e in ev if e.get("type") == "TEXT_MESSAGE_CONTENT")  # noqa: E731
    # the card waits (here: made to wait): the sentence comes before it
    monkeypatch.setattr(voice, "said_outright", lambda *a, **k: False)
    model.script = [say("", card)]
    ev = collect(guide, "my-1", message=line, state=start(guide, LOAN))
    kinds = [(e["type"], e.get("name")) for e in ev]
    assert "Date of birth: July 1. Which year?" in said(ev)
    assert kinds.index(("TEXT_MESSAGE_CONTENT", None)) < kinds.index(("CUSTOM", "on_interrupt"))
    # the model said it itself: no second line; a whole date in the line: no line
    model.script = [say("The year of birth is missing: which year?", card)]
    assert "Which year?" not in said(collect(guide, "my-2", message=line, state=start(guide, LOAN)))
    model.script = [say("", card)]
    assert "Which year?" not in said(collect(guide, "my-3", message="my name is Anna Rossi, born 1st July 1991", state=start(guide, LOAN)))
    monkeypatch.undo()
    # the card is applied at once: no line, the year question card follows and asks
    model.script = [say("", card)]
    ev = collect(guide, "my-4", message=line, state=start(guide, LOAN))
    raw = next(e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt")
    assert (json.loads(raw) if isinstance(raw, str) else raw).get("quiet") is True and "Which year?" not in said(ev)


def test_the_three_switches_of_the_measurement(guide, model, monkeypatch):
    """B, C, D from the supplier's guidance (the CPO's order, 2026-11-17), each off by default.
    B: no "none of these"; a target counts by its top probability and lead, a value on its companion's yes.
    C: "asks more" is the surer of two single questions. D: a yes / no under 0.7 is unknown."""
    from formguide.site import guide as site_guide
    from formguide.intent_external import ExternalChooser
    P = intent.Pick
    chooser = Mock()
    layer = intent.Layer(intent.Settings(provider="jev"), chooser)
    raw = {"target": P("screen:/loans", 0.9), "value": P("loan_type=auto", 0.9), "gives_value": P("no", 0.8), "is_command": P("yes", 0.6),
           "asks_fact": P("no", 0.9), "asks_text": P("yes", 0.8)}
    assert site_guide._refined(raw, layer) == raw                                      # all off: untouched
    q = intent.Question("choice", "target", "Which?", (intent.Option("a", "A"),))
    assert "none" in ExternalChooser._wire(q)["criteria"]
    monkeypatch.setenv("INTENT_COMPANION", "1")
    assert "none" not in ExternalChooser._wire(q)["criteria"]                         # no "none of these"
    assert "none" in ExternalChooser._wire(intent.Question("choice", "all_of", "Which?", (intent.Option("a", "A"),)))["criteria"]
    chooser.probs, chooser.ratios = {"target": {"screen:/loans": 0.73}}, {"target": 4.6}
    kept = site_guide._refined(raw, layer)
    assert "target" in kept and "value" not in kept                                    # a clear target; no yes for the value
    chooser.probs, chooser.ratios = {"target": {"screen:/loans": 0.55}}, {"target": 1.4}
    assert "target" not in site_guide._refined(raw, layer)                             # two options close: not taken
    monkeypatch.delenv("INTENT_COMPANION")
    monkeypatch.setenv("INTENT_SPLIT", "1")
    more = site_guide._refined(raw, layer)["asks_more"]
    assert more.id == "yes" and more.confidence == 0.8
    monkeypatch.delenv("INTENT_SPLIT")
    monkeypatch.setenv("INTENT_BANDS", "1")
    assert "is_command" not in site_guide._refined(raw, layer)
    # a whole turn with all three on: a plain order still opens the page with no model
    for k in ("INTENT_COMPANION", "INTENT_SPLIT"):
        monkeypatch.setenv(k, "1")
    plain = Mock(is_command=("yes", 0.9), kind=("go_to", 0.9), asks_move=("yes", 0.9), target=("screen:/loans", 0.95),
                 asks_fact=("no", 0.9), asks_text=("no", 0.9))
    before = len(model.calls)
    ev = run(site_with(guide, plain), "sw-1", message="open loans", state={"page": {"path": "/"}})
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before
    asked = plain.seen[0][1]
    assert {"asks_fact", "asks_text"} <= set(asked) and "asks_more" not in asked and "needs_agent" not in asked
