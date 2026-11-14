"""A blocking form rule is not a refusal, and a value the field already has makes no card."""
from __future__ import annotations

from formguide.agent.prompts import CORE

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value


def _filled(guide, **values):
    state = start(guide, LOAN)
    state["config"] = LOAN.compute({**state["config"]["state"], **values})
    return state


def _tool_text(model):
    return " ".join(str(m.content) for call in model.calls for m in call if getattr(m, "type", "") == "tool")


def test_a_value_the_field_already_has_makes_no_card_row(guide, model):
    state = _filled(guide, last_name="Morozova")
    model.script = [say("", ("c1", "propose_changes", {"changes": [{"name": "last_name", "value": "Morozova"},
                                                                    {"name": "first_name", "value": "Anna"}]}))]
    v = interrupt_value(collect(guide, "nr1", message="fill my name", state=state))
    assert [c["name"] for c in v["changes"]] == ["first_name"]   # the card claims only what changes


def test_only_unchanged_values_make_no_card_at_all(guide, model):
    state = _filled(guide, loan_type={"id": "consumer", "name": "Consumer loan"})
    model.script = [say("", ("c1", "propose_changes", {"changes": [{"name": "loan_type", "value": "consumer"}]})),
                    say("The loan type is already Consumer loan.")]
    ev = collect(guide, "nr2", message="set the loan type to consumer", state=state)
    assert interrupt_value(ev) is None
    assert "already has this value" in _tool_text(model)


def test_the_prompt_keeps_helping_past_a_blocking_rule():
    text = " ".join(CORE.split())
    assert "is the form's rule, not yours" in text and "Never refuse to go on" in text
    assert "What you say matches what you do" in text
    assert "act, never only tell" in text and "Take me there" in text
