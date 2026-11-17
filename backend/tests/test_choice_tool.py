"""The choice tool for Dushes (demo branch; openspec/changes/choice-tool): the model names the target, the server
ranks the screen's options, and what happens next depends on the answer and on the person's own words."""
from __future__ import annotations

from formguide import intent
from formguide.site import Dushes, SiteMap

from .conftest import say
from .test_intent_wired import SITE, Mock, directives, run, text


class Ranker(Mock):
    """A mock chooser that also ranks: `ranks` maps a word of the target to [(option id, probability), ...]."""

    def __init__(self, ranks=None, **answers):
        super().__init__(**answers)
        self.ranks, self.asked = ranks or {}, []

    async def rank(self, phrase, language, question, screen):
        self.asked.append((phrase, [o.id for o in question.options]))
        return next((r for word, r in self.ranks.items() if word in phrase.lower()), [])


def tool_site(guide, chooser, **settings):
    s = Dushes(guide, SiteMap.load(SITE))
    s.intent = intent.Layer(intent.Settings(provider="jev", threshold=0.5, timeout_ms=200, **settings), chooser)
    return s


def tool_result(model, call_id):
    return next(m.content for m in model.calls[-1] if getattr(m, "tool_call_id", None) == call_id)


def call(cid, what, among=("screens",)):
    return say("", (cid, "choose_on_screen", {"what": what, "among": list(among)}))


HOME = {"page": {"path": "/"}}


def test_a_pick_the_person_asked_for_is_sent_to_the_screen_and_ends_the_turn(guide, model):
    chooser = Ranker({"insurance": [("screen:/insurance", 0.93), ("screen:/insure", 0.31)]})
    site = tool_site(guide, chooser)
    model.script = [say("Full cover starts at 39 a month. Want me to open Car insurance?")]
    run(site, "ct-1", message="what does car insurance cost?", state=HOME)
    model.script = [call("c1", "Car insurance")]
    before = len(model.calls)
    ev = run(site, "ct-1", message="yes, that one", state=HOME)                  # not a direct command: the model's turn
    assert directives(ev) == [{"type": "navigate", "path": "/insurance"}]
    assert text(ev).startswith("Car insurance.") and len(model.calls) == before + 1          # one model call in all
    what, options = chooser.asked[-1]
    assert what == "Car insurance" and "screen:/insurance" in options and all(o.startswith("screen:") for o in options)
    # the next turn's model sees the line as its own last words
    model.script = [say("Full cover is 39 a month there.")]
    run(site, "ct-1", message="and what does full cover cost there?", state={"page": {"path": "/insurance"}})
    assert any(getattr(m, "content", "") == "Car insurance." for m in model.calls[-1])


def test_a_pick_the_person_did_not_ask_for_is_only_offered(guide, model):
    chooser = Ranker({"insurance": [("screen:/insurance", 0.93)]})
    model.script = [call("c2", "Car insurance"), say("Car insurance covers theft and damage. Want me to open Car insurance?")]
    ev = run(tool_site(guide, chooser), "ct-2", message="what does car insurance cover?", state=HOME)
    assert directives(ev) == [] and tool_result(model, "c2").startswith("Not opened: the person asked a question")


def test_two_that_fit_nothing_that_fits_and_a_chooser_that_is_not_there(guide, model):
    close = Ranker({"insurance": [("screen:/insurance", 0.62), ("screen:/insure", 0.58)]})
    model.script = [call("c3", "insurance"), say("Car insurance, or the quote form?")]
    ev = run(tool_site(guide, close), "ct-3", message="I want the insurance one", state=HOME)
    assert directives(ev) == [] and tool_result(model, "c3").startswith("Several fit: Car insurance; Get a car insurance quote")

    model.script = [call("c4", "gift cards"), say("There is no gift cards page; the closest is Barbershop.")]
    ev = run(tool_site(guide, Ranker({"gift": [("screen:/barbershop", 0.2)]})), "ct-4", message="I want gift cards", state=HOME)
    assert directives(ev) == [] and tool_result(model, "c4").startswith("Nothing on the site has that name")

    model.script = [call("c6", "Loans"), say("", ("n6", "navigate", {"path": "/loans"})), say("Here is Loans.")]
    ev = run(tool_site(guide, Mock()), "ct-6", message="I want the loans thing", state=HOME)   # this chooser cannot rank
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and "not available" in tool_result(model, "c6")


def test_a_target_with_a_phone_in_it_never_leaves_the_process(guide, model):
    private = Ranker({"request": [("screen:/apply", 0.99)]})
    model.script = [call("c5", "the request from +39 333 123 4567"), say("I cannot look that up here.")]
    run(tool_site(guide, private), "ct-5", message="I want the request from +39 333 123 4567", state=HOME)
    assert not private.asked and "not available" in tool_result(model, "c5")


def test_a_part_of_a_page_is_picked_as_page_and_part(guide, model):
    m = SiteMap.load(SITE)
    page = next(p for p in m.pages if p.parts)
    part = page.parts[0]
    parts = Ranker({part.title.lower().split()[0]: [(f"part:{page.path}#{part.id}", 0.95)]})
    model.script = [call("c7", f"{page.title}: {part.title}", ("parts",))]
    ev = run(tool_site(guide, parts), "ct-7", message=f"I want to see {part.title}", state=HOME)
    d = directives(ev)
    assert len(d) == 1 and d[0]["path"] == page.path and part.id in d[0].values() and text(ev).startswith(f"{part.title}.")


def test_the_tool_is_not_offered_when_the_layer_is_off_and_the_fourth_arm_ends_on_a_move(guide, model, monkeypatch):
    site = Dushes(guide, SiteMap.load(SITE))
    model.script = [say("Hi.")]
    run(site, "ct-off", message="hello", state=HOME)
    names = {(t.get("function") or t)["name"] if isinstance(t, dict) else t.name for t in model.bound}
    assert "choose_on_screen" not in names
    # the measurement's fourth arm: the agent's own navigate, the turn ended by the server's line, no chooser
    monkeypatch.setenv("INTENT_END_ON_MOVE", "1")
    model.script = [say("", ("n1", "navigate", {"path": "/loans"}))]
    before = len(model.calls)
    ev = run(site, "ct-arm4", message="open the loans page", state=HOME)
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and text(ev) == "Loans." and len(model.calls) == before + 1


def test_what_a_direct_command_is_in_code():
    for line in ("open the loans page", "Okay, can you open car insurance", "open it", "set the loan type to Car loan",
                 "please show me the prices", "now scroll down", "take me to contacts"):
        assert intent.is_direct(line), line
    for line in ("what does it cost?", "I was thinking about a loan", "Yeah, I said car insurance",
                 "opening hours on sunday", ""):
        assert not intent.is_direct(line), line


def test_open_x_with_a_question_mark_is_a_command_and_articles_do_not_count(guide, model):
    """The owner at the demo (2026-11-17): "open apply for loan ?" was answered with a description and "Want me to
    open Apply for a loan?". The verb at the start makes it a command, whatever mark ends it; the title is
    matched without its articles; and the chooser's doubt does not turn an explicit request into a question."""
    from formguide.site.agent import wants_to_go
    for line in ("open apply for loan ?", "open apply for loan", "can you open car insurance?", "CAN YOU OPEN IT ?"):
        assert intent.is_direct(line) and wants_to_go(line), line
    assert not wants_to_go("what does it cost to open an account?")
    unsure = Mock(is_command=("yes", 0.6), kind=("question", 0.7), section=("/apply", 0.4))    # the chooser doubts
    for page, line, path in (("/", "open apply for loan ?", "/apply"), ("/book", "open apply for loan", "/apply"),
                             ("/apply", "can you open car insurance?", "/insurance")):
        before = len(model.calls)
        ev = run(tool_site(guide, unsure), f"q-{len(model.calls)}-{len(line)}", message=line, state={"page": {"path": page}})
        assert directives(ev) == [{"type": "navigate", "path": path}], line
        assert len(model.calls) == before and len(text(ev).split()) <= 5, line                 # one short line, no model


def test_taking_up_an_offer_is_done_in_code(guide, model, monkeypatch):
    """"CAN YOU OPEN IT ?" after an offer took a whole model turn (3.7 s). The person agreed to exactly what was
    offered, so it is carried out at once; anything more than a yes or a pointing word is a new line for the model."""
    monkeypatch.setenv("INTENT_LABELS", "1")
    for line in ("open it", "CAN YOU OPEN IT ?", "yes please", "that one", "ok"):
        assert intent.takes_up(line), line
    for line in ("yes, but what does it cost?", "open the other one with the prices", "no", ""):
        assert not intent.takes_up(line) or line == "no", line
    site = tool_site(guide, Mock())
    model.script = [say("", ("n1", "navigate", {"path": "/contacts"})),
                    say("The office is open 9:00 to 13:00 on Saturday. Want me to open Contacts?")]
    ev = run(site, "tu-1", message="when is the bank open on Saturday?", state=HOME)
    assert directives(ev) == []                                              # a question: offered, not opened
    before = len(model.calls)
    ev = run(site, "tu-1", message="CAN YOU OPEN IT ?", state=HOME)
    assert directives(ev) == [{"type": "navigate", "path": "/contacts"}] and len(model.calls) == before
    assert "no model" in text(ev)
    # an offered form: its page opens at once and the form's assistant takes over there
    model.script = [say("", ("o1", "open_form", {"form_id": "loan_application", "note": "a car loan"})),
                    say("You apply online in about ten minutes. Want me to open the loan application?")]
    run(site, "tu-2", message="how can I get a car loan?", state=HOME)
    before = len(model.calls)
    ev = run(site, "tu-2", message="yes please", state=HOME)
    d = directives(ev)
    assert len(d) == 1 and d[0]["path"] == "/apply" and d[0]["form_id"] == "loan_application" and len(model.calls) == before
    # more than a yes: the model's line
    model.script = [say("", ("n2", "navigate", {"path": "/contacts"})), say("Saturday 9:00 to 13:00. Want me to open Contacts?")]
    run(site, "tu-3", message="when is the bank open on Saturday?", state=HOME)
    model.script = [say("Sunday it is closed.")]
    before = len(model.calls)
    ev = run(site, "tu-3", message="yes, but what about Sunday?", state=HOME)
    assert directives(ev) == [] and len(model.calls) == before + 1


def test_the_tool_only_arm_puts_every_line_to_the_model(guide, model, monkeypatch):
    """INTENT_LAYER=0, for the QA Lead's measurement: the layer and the code shortcuts are off, the tool stays."""
    monkeypatch.setenv("INTENT_LAYER", "0")
    chooser = Ranker({"loans": [("screen:/loans", 0.95)]}, is_command=("yes", 0.98), kind=("go_to", 0.97), section=("/loans", 0.93))
    site = tool_site(guide, chooser)
    model.script = [call("c1", "Loans")]
    before = len(model.calls)
    ev = run(site, "arm2-1", message="open the loans page", state=HOME)
    assert len(model.calls) == before + 1 and not chooser.seen                 # the model was asked, the layer was not
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and text(ev).startswith("Loans.")
    names = {(t.get("function") or t)["name"] if isinstance(t, dict) else t.name for t in model.bound}
    assert "choose_on_screen" in names


OWNERS_12 = [   # the owner's 100 s of voice at the demo (2026-11-17), as the recogniser heard them
    ("/", "open a barbershop", "/barbershop"),
    ("/barbershop", "open car insurance", "/insurance"),
    ("/insurance", "open uh get a car insurance quote", "/insure"),
    ("/insure", "open apply for a loan", "/apply"),
    ("/", "open apply for a loan", "/apply"),
    ("/apply", "open barbershop", "/barbershop"),
    ("/barbershop", "open loans", "/loans"),
    ("/", "Okay, can you help me loans", "/loans"),
    ("/", "Okay, can you open we quick visit page", "/book"),
    ("/", "Okay, can you open the loans", "/loans"),
    ("/", "Can you open the mortga-the-ges", "/loans"),
]


def test_the_owners_twelve_spoken_commands_are_carried_out_with_no_model(guide, model):
    """Seven of the twelve were carried out by the layer in his recording; the other five went to the model,
    though each was a command. With what stands around a name taken away, the name said word for word or heard
    nearly right at a clear margin, and tabs and sections as targets, all twelve are settled in code."""
    from .test_agent import start
    from .test_questions import LOAN
    unsure = Mock(is_command=("no", 0.6), kind=("other", 0.6))                  # the chooser is of no help here
    for page, line, path in OWNERS_12:
        before = len(model.calls)
        ev = run(tool_site(guide, unsure), f"own-{len(line)}-{before}", message=line, state={"page": {"path": page}})
        d = directives(ev)
        assert len(d) == 1 and d[0]["path"] == path and len(model.calls) == before, line
        assert len(text(ev).split()) <= 5, line                                    # one short line
    assert directives(run(tool_site(guide, unsure), "own-m", message="Can you open the mortga-the-ges",
                          state=HOME))[0].get("tab") == "mortgage"
    # the twelfth: a section of the form on the screen
    before = len(model.calls)
    ev = run(tool_site(guide, unsure), "own-12", message="Can you open personal details",
             state={"page": {"path": "/apply"}, "form": start(guide, LOAN)})
    assert [e.get("toolCallName") for e in ev if e.get("type") == "TOOL_CALL_START"] == ["focus_field"]
    assert len(model.calls) == before and text(ev).startswith("Personal details.")
    # what is not settled in code: a word that fits two names, and a place that is not named
    for line in ("open insurance", "open the prices"):
        model.script = [say("Which one do you mean?")]
        before = len(model.calls)
        run(tool_site(guide, unsure), f"own-x-{len(line)}", message=line, state=HOME)
        assert len(model.calls) == before + 1, line
