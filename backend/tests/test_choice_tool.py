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


def test_open_x_with_a_question_mark_is_a_command_and_articles_do_not_count(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_CODE", "1")   # the measurement's code arm: names settled in code, no chooser
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
    monkeypatch.setenv("INTENT_CODE", "1")   # the measurement's code arm
    """"CAN YOU OPEN IT ?" after an offer took a whole model turn (3.7 s). The person agreed to exactly what was
    offered, so it is carried out at once; anything more than a yes or a pointing word is a new line for the model."""
    monkeypatch.setenv("INTENT_LABELS", "1")
    for line in ("open it", "CAN YOU OPEN IT ?", "yes please", "that one", "ok"):
        assert intent.takes_up(line), line
    for line in ("yes, but what does it cost?", "open the other one with the prices", "no", ""):
        assert not intent.takes_up(line) or line == "no", line
    site = tool_site(guide, Mock())
    model.script = [say("", ("n1", "navigate", {"path": "/contacts", "asked": "question"})),
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
    ("/", "Okay, can you open the loans", "/loans"),
    ("/", "Can you open the mortga-the-ges", "/loans"),
]


def test_the_owners_twelve_spoken_commands_are_carried_out_with_no_model(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_CODE", "1")   # the measurement's code arm: names settled in code, no chooser
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
    # what is not settled in code: a word that fits two names, a place that is not named, and a line heard so badly
    # that no single name is near it ("we quick visit" for Book a visit: the model opened it, 1.6 s in his recording)
    for line in ("open insurance", "open the prices", "Okay, can you open we quick visit page"):
        model.script = [say("Which one do you mean?")]
        before = len(model.calls)
        run(tool_site(guide, unsure), f"own-x-{len(line)}", message=line, state=HOME)
        assert len(model.calls) == before + 1, line


def path_site(guide):
    """A site whose host can give a form's structure without the page (as the demo's does)."""
    from .test_agent import start
    from .test_questions import LOAN
    site = tool_site(guide, Mock(is_command=("no", 0.6), kind=("other", 0.6)))
    site.form_for = lambda form_id, ctx: {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": [], "focused": None}} \
        if form_id == "loan_application" else None
    return site


def test_a_path_through_the_hierarchy_is_carried_out_step_by_step(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_CODE", "1")   # the measurement's code arm: names settled in code, no chooser
    """The owner (2026-11-17): "we know the hierarchy ... apply loan -> application -> personal details, the whole
    way down to what is opened". A section of a form on another page: the page opens, then, when that page has
    loaded its form, the section, by the form's own step. No model in either step."""
    import json
    from .test_agent import start
    from .test_questions import LOAN
    for n, line in enumerate(("open apply for loan, application, personal details", "open passport in loan application")):
        site, thread = path_site(guide), f"path-{n}"
        before = len(model.calls)
        ev = run(site, thread, message=line, state=HOME)
        d = directives(ev)
        assert len(d) == 1 and d[0]["path"] == "/apply" and d[0]["form_id"] == "loan_application", line
        assert len(model.calls) == before and text(ev).startswith("Apply for a loan."), line
        # the page has loaded its form: the browser's hand-off run opens the section
        ev = run(site, thread, handoff=True, state={"page": {"path": "/apply"}, "form": start(guide, LOAN)})
        args = [json.loads(e["delta"]) for e in ev if e.get("type") == "TOOL_CALL_ARGS"]
        want = "acc_personal" if n == 0 else "acc_passport"
        assert [e.get("toolCallName") for e in ev if e.get("type") == "TOOL_CALL_START"] == ["focus_field"], line
        assert args[0]["name"] == want and len(model.calls) == before, line
        assert text(ev).startswith("Personal details." if n == 0 else "Passport."), line
    # a tab of another page, from any page
    for page in ("/", "/barbershop", "/apply"):
        before = len(model.calls)
        ev = run(path_site(guide), f"path-m-{len(page)}", message="open the mortgage", state={"page": {"path": page}})
        d = directives(ev)
        assert len(d) == 1 and d[0]["path"] == "/loans" and d[0].get("tab") == "mortgage" and len(model.calls) == before
        assert text(ev).startswith("Mortgage.")
    # a page whose own name holds a word that is also a tab of its form ("Apply for a loan" and the tab "Loan"):
    # the line names the page (seen live: it opened the page and then the tab)
    ev = run(path_site(guide), "path-p", message="open apply for a loan", state=HOME)
    d = directives(ev)
    assert len(d) == 1 and d[0]["path"] == "/apply" and "form_id" not in d[0] and "then the section" not in text(ev)
    # a name that is both a page and a section of a form: the page, unless the way to the section is said
    assert directives(run(path_site(guide), "path-c1", message="open contacts", state=HOME)) == [{"type": "navigate", "path": "/contacts"}]
    d = directives(run(path_site(guide), "path-c2", message="open contacts in the loan application", state=HOME))
    assert d[0]["path"] == "/apply" and d[0].get("form_id") == "loan_application"


def test_a_bare_date_goes_into_the_date_field_in_sight(guide, model, monkeypatch):
    monkeypatch.setenv("INTENT_CODE", "1")   # the measurement's code arm: names settled in code, no chooser
    """The owner said "1st July 2014" with Personal details open, and it went to the model. A date is never a place
    to go, but it is a value: with one date field in the open section it goes into that field through the form's
    own card (its checks and Undo apply). No section open, or two date fields in sight: one question from the agent."""
    import json
    from .test_agent import start
    from .test_questions import LOAN

    def state(opened, focused=None):
        return {"page": {"path": "/apply"}, "form": {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": opened, "focused": focused}}}

    def card(ev):
        raw = next((e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "on_interrupt"), None)
        return (json.loads(raw) if isinstance(raw, str) else raw) if raw else None

    site = path_site(guide)
    before = len(model.calls)
    c = card(run(site, "date-1", message="1st July 2014", state=state(["acc_personal"])))
    assert c and c["changes"][0]["name"] == "birth_date" and str(c["changes"][0]["value"]).startswith("2014-07-01")
    assert c.get("quiet") is True and len(model.calls) == before
    # the field that has the focus decides between two
    c = card(run(site, "date-2", message="01.07.2014", state=state(["acc_personal", "acc_passport"], "passport_issued_date")))
    assert c and c["changes"][0]["name"] == "passport_issued_date"
    # nothing open, or two date fields in sight and none focused: the agent's line
    for opened in ([], ["acc_personal", "acc_passport"]):
        model.script = [say("Is that your date of birth or the passport's date of issue?")]
        before = len(model.calls)
        ev = run(site, f"date-3-{len(opened)}", message="1st July 2014", state=state(opened))
        assert card(ev) is None and len(model.calls) == before + 1
    # a date in a line never moves the person
    model.script = [say("Which day do you want to book?")]
    assert directives(run(site, "date-4", message="open 1st July 2014", state=HOME)) == []


def test_the_matcher_takes_its_names_from_the_hosts_map_in_any_of_the_languages():
    """The owner: "how do we make this generic?" No word of a site is in the code: every name comes from the map
    the host gives. The same matcher, unchanged, on a cabinet-like map (Today, Site, Requests, Settings) in
    Russian and in Italian; the words around a name (fillers, politeness, articles, the verb) are the language's."""
    ru = {"today": "\u0421\u0435\u0433\u043e\u0434\u043d\u044f", "site": "\u0421\u0430\u0439\u0442", "requests": "\u0417\u0430\u044f\u0432\u043a\u0438", "settings": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"}
    it = {"today": "Oggi", "site": "Sito", "requests": "Richieste", "settings": "Impostazioni"}
    for names, lines in ((ru, [("\u043e\u0442\u043a\u0440\u043e\u0439 \u0437\u0430\u044f\u0432\u043a\u0438", "requests"), ("\u043f\u043e\u043a\u0430\u0436\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438", "settings"), ("\u043e\u0442\u043a\u0440\u043e\u0439, \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0441\u0430\u0439\u0442", "site"), ("\u043c\u043e\u0436\u0435\u0448\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u0437\u0430\u044f\u0432\u043a\u0438", "requests"), ("\u043d\u0443 \u043e\u0442\u043a\u0440\u043e\u0439 \u0437\u0430\u044f\u0432\u043a\u0443", "requests"), ("\u043f\u043e\u043a\u0430\u0436\u0438 \u043c\u043d\u0435 \u0441\u0435\u0433\u043e\u0434\u043d\u044f", "today")]),
                         (it, [("apri le richieste", "requests"), ("puoi aprire le impostazioni", "settings"), ("mostra oggi", "today"), ("apri il sito per favore", "site"), ("apri la pagina delle impostazioni", "settings")])):
        targets = [{"id": i, "label": label, "kind": "page", "up": []} for i, label in names.items()]
        for line, want in lines:
            assert intent.is_direct(line) or intent.asks_for(line), line
            assert intent.match_path(line, targets) == (want, "said"), line
        # a page the map does not have is not guessed
        assert intent.match_path(lines[0][0].split()[0] + " zzzqqq", targets) is None


def test_the_chooser_is_told_what_the_forms_assistant_is_told_and_nothing_private(guide, model):
    """The owner (2026-11-17): the chooser gets about the context the form's assistant gets: the screen, the form's
    structure with what is filled (personal data as "<filled>"), what was offered and opened last, and the last
    ten messages of both sides. Everything passes the filter: a phone, an e-mail or a long number never leaves."""
    from formguide.transcript import new_entry
    from .test_agent import start
    from .test_questions import LOAN
    chooser = Mock(is_command=("yes", 0.9), kind=("other", 0.9))
    site = tool_site(guide, chooser)
    tx = site.forms.transcripts
    for i in range(7):
        tx.append("ctx-1", new_entry("user", text=f"line {i}"))
        tx.append("ctx-1", new_entry("assistant", text=f"answer {i}"))
    tx.append("ctx-1", new_entry("user", text="my phone is +39 333 123 4567 and mail anna@aster.example"))
    site._offers["ctx-1"] = {"tool": "navigate", "args": {"path": "/insure"}, "title": "Get a car insurance quote"}
    site.__dict__.setdefault("_last", {})["ctx-1"] = "Car insurance"
    form = {**start(guide, LOAN), "ui": {"activeTabs": {}, "openAccordions": ["acc_personal"], "focused": "birth_date"}}
    model.script = [say("Which one?")]
    run(site, "ctx-1", message="the other one", state={"page": {"path": "/apply"}, "form": form})
    ctx = chooser.context
    assert ctx["page"] == "Apply for a loan" and ctx["open_sections"] == ["Personal details"] and ctx["field_in_focus"] == "Date of birth"
    assert ctx["offered"] == ["Get a car insurance quote"] and ctx["opened_last"] == "Car insurance"
    assert len(ctx["last_messages"]) == 10 and ctx["last_messages"][-1].startswith("person: my phone is <filled>")
    assert "anna@aster.example" not in str(ctx) and "333" not in str(ctx)
    assert "Personal details" in ctx["form"] and "Date of birth" in ctx["form"]            # the form, as its assistant reads it
    # the whole site goes as paths, a form's sections on other pages included
    labels = [o.label for o in chooser.seen[-1][1]["target"].options]
    assert "Loans" in labels and "Loans \u203a Mortgage" in labels
    assert "Apply for a loan \u203a Applicant \u203a Personal details" in labels
    assert intent.scrub(site.intent, "call 030 1234567 or anna@aster.example") == "call <filled> or <filled>"


def test_the_code_only_arm_asks_no_chooser(guide, model, monkeypatch):
    """INTENT_CODE=1, the measurement's fifth arm: what the names said settle is carried out; nothing else is
    put to the chooser. It is a switch for measuring, never the default."""
    monkeypatch.setenv("INTENT_CODE", "1")
    chooser = Mock(is_command=("yes", 0.98), kind=("go_to", 0.97), section=("/loans", 0.93))
    site = tool_site(guide, chooser)
    before = len(model.calls)
    ev = run(site, "code-1", message="open the loans page", state=HOME)
    assert directives(ev) == [{"type": "navigate", "path": "/loans"}] and len(model.calls) == before and not chooser.seen
    model.script = [say("The rates are on the Loans page.")]
    run(site, "code-2", message="show the interest rate", state=HOME)       # code cannot settle it: the model, no chooser
    assert not chooser.seen and len(model.calls) == before + 1
