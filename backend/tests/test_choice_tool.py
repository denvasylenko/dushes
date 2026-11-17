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
    for line in ("what does it cost?", "I was thinking about a loan", "Yeah, I said car insurance", "can you open it?",
                 "opening hours on sunday", ""):
        assert not intent.is_direct(line), line
