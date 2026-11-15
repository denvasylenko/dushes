"""Sending: what the form reports (`submitted` on its root), and an agent with no tool that sends."""
from __future__ import annotations

from formguide.agent.prompts import sending

from .conftest import can_send, say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value, tool_result


def _run(guide, model, thread, state=None, **kw):
    model.script = [say("Hello.")]
    collect(guide, thread, message="was it sent?", state=state or start(guide, LOAN), **kw)
    names = {(t.get("function") or t)["name"] if isinstance(t, dict) else t.name for t in model.bound}
    last = model.calls[-1][-1].content
    text = last if isinstance(last, str) else " ".join(b.get("text", "") for b in last if isinstance(b, dict))
    return names, text, model.calls[-1][0].content


def test_without_a_tool_that_sends_there_is_nothing_to_confirm(guide, model):
    names, context, system = _run(guide, model, "s1")
    assert "confirm_action" not in names and "review_form" in names
    assert "SENDING: you have no tool that sends this form" in context and "form's own send button" in context
    assert "confirm_action" not in system                      # the rule about asking first is not in the prompt


def test_a_host_tool_or_a_page_tool_keeps_the_confirmation(guide, model):
    page_tool = [{"name": "send_it", "description": "Send the form", "parameters": {"type": "object", "properties": {}}}]
    names, context, _ = _run(guide, model, "s2", client_tools=page_tool)
    assert "confirm_action" in names and "SENDING" not in context
    names, context, system = _run(can_send(guide), model, "s3")
    assert "confirm_action" in names and "SENDING" not in context and "confirm_action" in system


def test_the_form_says_it_was_sent(guide, model):
    state = start(guide, LOAN)
    root = guide.layout(state["jsx_hash"]).root
    state["config"]["props"].setdefault(root, {})["submitted"] = {"reference": "A-118", "at": "2026-11-15 10:02"}
    _, context, _ = _run(guide, model, "s4", state=state)
    assert "SENT: this form has been sent, reference A-118, at 2026-11-15 10:02" in context
    assert "SENDING" not in context
    state["config"]["props"][root]["submitted"] = False
    _, context, _ = _run(can_send(guide), model, "s5", state=state)
    assert "NOT SENT: this form has not been sent yet." in context


def test_the_line_itself():
    assert sending(None, True) == ""
    assert sending(True, False).startswith("SENT: this form has been sent.")
    chat_only = sending(None, False, hidden=True)
    assert "this chat cannot send them" in chat_only and "send button" not in chat_only
    assert sending(False, False).startswith("NOT SENT") and "SENDING" in sending(False, False)


def test_a_review_before_sending_offers_no_send_button(guide, model):
    model.script = [say("", ("r1", "review_form", {"mode": "submit"}))]
    v = interrupt_value(collect(guide, "s6", message="send it", state=start(guide, LOAN)))
    assert v["type"] == "review" and v["mode"] == "status"     # nothing here sends: no Send button on the card
    model.script = [say("Ok.")]
    collect(guide, "s6", resume={"action": "submit"})          # an older client may still answer "submit"
    out = tool_result(model, "r1")
    assert "no tool that sends it" in out and "confirm_action" not in out
