"""A form the person does not see (ui.form_visible: false): no pointing at the page, and the agent is told."""
from __future__ import annotations

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN


def _run(guide, model, thread, visible):
    state = start(guide, LOAN)
    if visible is not None:
        state["ui"] = {"form_visible": visible}
    model.script = [say("What is your last name?")]
    collect(guide, thread, message="help me apply", state=state)
    names = {(t.get("function") or t)["name"] if isinstance(t, dict) else t.name for t in model.bound}
    last = model.calls[-1][-1].content
    text = last if isinstance(last, str) else " ".join(b.get("text", "") for b in last if isinstance(b, dict))
    return names, text, model.calls[-1][0].content


def test_a_hidden_form_offers_no_pointing_and_says_so(guide, model):
    names, context, system = _run(guide, model, "hf1", False)
    assert "focus_field" not in names and "propose_changes" in names and "ask_user" in names
    assert "THE PERSON DOES NOT SEE THIS FORM" in context
    assert "Showing where" not in system                       # the rules about pointing are not in the prompt


def test_a_visible_form_is_as_before(guide, model):
    for i, visible in enumerate((None, True)):
        names, context, _ = _run(guide, model, f"hf{i + 2}", visible)
        assert "focus_field" in names and "DOES NOT SEE" not in context
