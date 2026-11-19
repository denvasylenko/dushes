"""The owner's transcript from a host without the choice layer (2026-11-19): a direct "navigate me to …" and
"navigate me back" were met with "would you like me to open it?" and "which page?", and a misspelt "nvigate me
back" could not move at all, because a word list decided whether the agent may move.

The model is scripted, so what is checked here is the server's side of every step: what the agent is told (the
trail and the page before this one, with its path), and that the move it then makes is carried out, whatever the
spelling of the line. Whether a real model makes that move is the QA Lead's live scenario."""
from __future__ import annotations

from .conftest import say
from .test_site import run, site  # noqa: F401 - the fixture


def _moves(ev):
    return [e["value"].get("path") for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "site_directive"]


def _told(model):
    """Everything the agent was shown for the turn's first model call."""
    return "\n".join(str(getattr(m, "content", "")) for m in model.calls[-2])


def _result(model, call_id):
    return next(str(m.content) for m in model.calls[-1] if getattr(m, "tool_call_id", None) == call_id)


def test_the_owners_transcript_back_and_a_direct_move_at_once(site, model):
    # 1. "navigate me to my requests": the page opens in this turn
    model.script = [say("", ("n1", "navigate", {"path": "/loans", "asked": "ordered"})), say("Loans.")]
    ev = run(site, "tr1", message="navigate me to loans", state={"page": {"path": "/procurement"}})
    assert _moves(ev) == ["/loans"]

    # 2. "navigate me back": the agent is told which page was open before this one, and the move is carried out
    model.script = [say("", ("n2", "navigate", {"path": "/procurement", "asked": "back"})), say("Purchase request.")]
    ev = run(site, "tr1", message="navigate me back", state={"page": {"path": "/loans"}})
    assert "The page before this one: Purchase request (/procurement)" in _told(model)
    assert _moves(ev) == ["/procurement"] and "Not opened" not in _result(model, "n2")

    # 3. "what my first message?": a question, nothing moves
    model.script = [say("Your first message was \"navigate me to loans\".")]
    assert _moves(run(site, "tr1", message="what my first message?", state={"page": {"path": "/procurement"}})) == []

    # 5. "navigate me back to where I asked initially"
    model.script = [say("", ("n5", "navigate", {"path": "/procurement", "asked": "ordered"})), say("Purchase request.")]
    run(site, "tr1", message="navigate me back to where I asked initially", state={"page": {"path": "/procurement"}})

    # 6. "nvigate me back", misspelt: the page before this one is still Loans, and the move is carried out
    #    (it was refused: no word of the list is in the line)
    model.script = [say("", ("n6", "navigate", {"path": "/loans", "asked": "back"})), say("Loans.")]
    ev = run(site, "tr1", message="nvigate me back", state={"page": {"path": "/procurement"}})
    assert "The page before this one: Loans (/loans)" in _told(model)
    assert _moves(ev) == ["/loans"] and "Not opened" not in _result(model, "n6")

    # 7. "where I was couple of messages before?": a question; the agent's own reading keeps the person here
    model.script = [say("", ("n7", "navigate", {"path": "/procurement", "asked": "question"})),
                    say("You were on Purchase request. Want me to open it?")]
    ev = run(site, "tr1", message="where I was couple of messages before?", state={"page": {"path": "/loans"}})
    assert _moves(ev) == [] and _result(model, "n7").startswith("Not opened")


def test_the_agents_own_moves_are_the_trail_on_a_host_that_sends_no_page(site, model):
    model.script = [say("", ("a1", "navigate", {"path": "/loans", "asked": "ordered"})), say("Loans.")]
    run(site, "tr2", message="open loans", state={})
    model.script = [say("", ("a2", "navigate", {"path": "/contacts", "asked": "ordered"})), say("Contacts.")]
    run(site, "tr2", message="now the contacts", state={})
    model.script = [say("", ("a3", "navigate", {"path": "/loans", "asked": "back"})), say("Loans.")]
    ev = run(site, "tr2", message="zurück bitte", state={})
    assert "The page before this one: Loans (/loans)" in _told(model) and _moves(ev) == ["/loans"]


def test_the_rules_say_back_and_a_direct_move_are_done_at_once(site, model):
    model.script = [say("Hello.")]
    run(site, "tr3", message="hello", state={"page": {"path": "/"}})
    rules = str(model.calls[-1][0].content)
    assert "the page that was open before this one" in rules and "without asking where" in rules
    assert 'Never ask "would you like me to open it?"' in rules


def test_the_word_list_decides_again_under_the_switch(site, model, monkeypatch):
    monkeypatch.setenv("INTENT_GATE", "words")
    model.script = [say("", ("w1", "navigate", {"path": "/loans", "asked": "back"})), say("Which page?")]
    ev = run(site, "tr4", message="nvigate me back", state={"page": {"path": "/procurement"}})
    assert _moves(ev) == [] and _result(model, "w1").startswith("Not opened")
