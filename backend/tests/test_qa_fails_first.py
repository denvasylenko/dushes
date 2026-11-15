"""QA's "fails first" checks for fixes the Owner has on his list (the CPO, 2026-11-15). Each is marked xfail(strict):
the suite stays green while the defect is there, and the mark must come off in the commit that fixes it (a strict
xfail that passes fails the suite). Nothing here calls a real model.

1. A tool that raises must still leave its tool call with an output. On 2026-11-15 gpt-6-luna called get_outline
   with a container that does not exist ("1.1.1"); the server raised KeyError, the guest got no reply, and the next
   request was rejected by OpenAI: "No tool output found for function call" (7 conversations of 253).
2. The site assistant's turns must report their tokens: a conversation answered by Dushes alone showed 0 tokens, so
   the spend lock of a run (evals.py --max-usd) and the cost per turn do not see its calls.
The third, "the agent never agrees for the person", needs a model: evals/consent_not_given_car_rental.yaml.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.messages import ToolMessage

from demo.mock_forms import FORMS

from .conftest import say

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

LOAN = FORMS["loan_application"]


def collect(guide, thread, **kw) -> list[dict]:
    async def go():
        return [e async for e in guide.run(thread, **kw)]
    return asyncio.run(go())


def test_a_tool_that_raises_still_answers_its_call_and_the_guest(guide, model):
    model.script = [say("", ("t1", "get_outline", {"container": "1.1.1"})),   # no such container
                    say("That part of the form is not there; here is what I can see instead."),
                    say("Yes, I am here.")]
    info = guide.register_form(LOAN.jsx, LOAN.form_id, LOAN.domain)
    state = {"config": LOAN.compute(None), "jsx_hash": info["jsx_hash"], "form_id": LOAN.form_id, "ui": {}}
    ev = collect(guide, "th", message="please fill in my application", state=state)
    assert not [e for e in ev if e["type"] == "RUN_ERROR"], "the run ended in an error the guest sees as silence"
    assert any(e["type"] == "TEXT_MESSAGE_CONTENT" for e in ev), "the guest got no reply after the tool failed"
    answered = [m for m in model.calls[1] if isinstance(m, ToolMessage) and m.tool_call_id == "t1"]
    assert answered and "1.1.1" in str(answered[0].content), "the failed call has no tool output for the model to read"
    ev = collect(guide, "th", message="hello? did the form get filled in?", state=state)   # the next turn must not be rejected
    assert not [e for e in ev if e["type"] == "RUN_ERROR"] and any(e["type"] == "TEXT_MESSAGE_CONTENT" for e in ev)
    for call in model.calls[1:]:   # every tool call in the history sent to the model has its output (OpenAI refuses otherwise)
        ids = {tc["id"] for m in call for tc in getattr(m, "tool_calls", None) or []}
        assert ids <= {m.tool_call_id for m in call if isinstance(m, ToolMessage)}


def test_a_turn_answered_by_the_site_assistant_reports_its_tokens(tmp_path):
    import evals
    from harness_client import Visit
    http = evals.offline_client(tmp_path / "data")
    v = Visit(http, "/")                       # the home page: no form, Dushes answers by itself
    v.say("When is the bank open on Saturday?")
    assert any(str(x).startswith("\U0001f916") for x in v.log), "the site assistant did not answer"
    assert v.stats, "no run_stats event for a turn the site assistant answered: its tokens are invisible"
    assert {"input", "output"} <= set(v.tokens), "run_stats carries no token counts"
