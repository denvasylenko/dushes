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
    assert "failed" in result["content"] and result["error"] is True   # a client need not guess from the words


def test_get_outline_takes_an_outline_number(guide, model):
    model.script = [say("", ("o1", "get_outline", {"container": "1.1", "depth": 2})), say("Here it is.")]
    ev = collect(guide, "tr2", message="show the first tab", state=start(guide, LOAN))
    assert ev[-1]["type"] == "RUN_FINISHED" and "failed" not in tool_result(model, "o1")
    assert "error" not in next(e for e in ev if e["type"] == "TOOL_CALL_RESULT" and e["toolCallId"] == "o1")


def test_open_calls_of_a_broken_turn_get_error_results():
    call = {"id": "c1", "name": "get_fields", "args": {}}
    other = {"id": "c2", "name": "get_field", "args": {}}
    broken = [HumanMessage("hi"), AIMessage(content="", tool_calls=[call, other]), ToolMessage("ok", tool_call_id="c1")]
    fixed = _unanswered(broken)
    assert [r["id"] for r in fixed] == ["c2"] and fixed[0]["error"] and "previous turn ended" in fixed[0]["content"]
    assert _unanswered([*broken, ToolMessage("x", tool_call_id="c2")]) == []
    assert _unanswered([HumanMessage("hi"), AIMessage(content="Hello.")]) == []


def test_line_separators_never_cut_an_event():
    """From the review of the Swift client (2026-11-15): URLSession's bytes.lines, like other SSE readers, splits on
    U+2028, U+2029 and U+0085, which JSON allows raw inside a string. They go out escaped."""
    import json

    from formguide import agui
    text = "a b c\u0085d"
    out = agui.encode({"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": text})
    assert not any(ch in out for ch in "  \u0085") and out.endswith("\n\n")
    assert len(out.splitlines()) == 2                                  # the data line and the empty line, nothing more
    assert json.loads(out[len("data: "):])["delta"] == text           # a client reads the same text back
    bad = agui.encode({"type": "NO_SUCH_EVENT", "note": text})        # the fallback path escapes too
    assert not any(ch in bad for ch in "  \u0085") and json.loads(bad[len("data: "):])["note"] == text


def test_a_failed_step_says_so_on_its_result():
    from formguide import agui
    out = agui.encode({"type": "TOOL_CALL_RESULT", "messageId": "m", "toolCallId": "c", "content": "x", "role": "tool",
                       "error": True})
    assert '"error":true' in out.replace(" ", "")                     # the event model keeps the flag


def test_a_silent_stream_sends_a_keep_alive_line():
    """The widget designer, for the cabinet's watchdog (2026-11-15): a healthy run can be silent for a long time
    (a tool at work; up to two minutes waiting for the thread's previous turn), and nothing told a client that the
    connection was alive. A comment line now goes out after every stretch of silence."""
    import asyncio

    from formguide import agui

    async def run_stream():
        yield "data: 1\n\n"
        await asyncio.sleep(0.16)          # a slow tool
        yield "data: 2\n\n"

    async def read(every):
        return [c async for c in agui.alive(run_stream(), every=every)]

    got = asyncio.run(read(0.05))
    assert got[0] == "data: 1\n\n" and got[-1] == "data: 2\n\n"
    assert 2 <= got.count(agui.KEEPALIVE) <= 4 and agui.KEEPALIVE.startswith(":")   # an SSE comment, not an event
    assert asyncio.run(read(0)) == ["data: 1\n\n", "data: 2\n\n"]                    # switched off: untouched

    async def broken():
        yield "data: 1\n\n"
        raise RuntimeError("the run broke")

    async def read_broken():
        return [c async for c in agui.alive(broken(), every=0.05)]

    try:
        asyncio.run(read_broken())
        raise AssertionError("an error inside the run must reach the reader")
    except RuntimeError as e:
        assert "the run broke" in str(e)
