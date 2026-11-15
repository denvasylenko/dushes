"""Every tool call gets a result: a crash inside a tool, and a turn that broke off, never leave a call open."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from formguide.agent import tools
from formguide.agent.graph import _unanswered

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, tool_result


def test_a_crash_inside_a_tool_is_an_error_result(guide, model, monkeypatch):
    def boom(a, ctx):
        raise KeyError("1.1")
    monkeypatch.setattr(tools, "_t_get_fields", boom)
    model.script = [say("", ("g1", "get_fields", {"container": "tab_applicant"})), say("I could not read that part.")]
    ev = collect(guide, "tr1", message="what is on the first tab?", state=start(guide, LOAN))
    assert ev[-1]["type"] == "RUN_FINISHED"                        # the turn goes on
    out = tool_result(model, "g1")
    assert "get_fields failed (KeyError)" in out
    result = next(e for e in ev if e["type"] == "TOOL_CALL_RESULT" and e["toolCallId"] == "g1")
    assert "failed" in result["content"]


def test_get_outline_takes_an_outline_number(guide, model):
    model.script = [say("", ("o1", "get_outline", {"container": "1.1", "depth": 2})), say("Here it is.")]
    ev = collect(guide, "tr2", message="show the first tab", state=start(guide, LOAN))
    assert ev[-1]["type"] == "RUN_FINISHED" and "failed" not in tool_result(model, "o1")


def test_open_calls_of_a_broken_turn_get_error_results():
    call = {"id": "c1", "name": "get_fields", "args": {}}
    other = {"id": "c2", "name": "get_field", "args": {}}
    broken = [HumanMessage("hi"), AIMessage(content="", tool_calls=[call, other]), ToolMessage("ok", tool_call_id="c1")]
    fixed = _unanswered(broken)
    assert [r["id"] for r in fixed] == ["c2"] and fixed[0]["error"] and "previous turn ended" in fixed[0]["content"]
    assert _unanswered([*broken, ToolMessage("x", tool_call_id="c2")]) == []
    assert _unanswered([HumanMessage("hi"), AIMessage(content="Hello.")]) == []
