"""The agent graph with a scripted model: tool calls, interrupt, skills, extra tools, HTTP router."""
from __future__ import annotations

import json

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, ToolMessage

from demo.mock_forms import FORMS
from formguide.agent.graph import is_note
from formguide.agent.tools import ToolCtx, ToolError, run_tool
from formguide.form.overlay import DepStore, Overlay
from formguide.form.render import locate
from formguide.server import create_router

from .conftest import say

LOAN = FORMS["loan_application"]
BARBER = FORMS["barber_booking"]


def collect(guide, thread, **kw) -> list[dict]:
    async def go():
        return [e async for e in guide.run(thread, **kw)]
    return asyncio.run(go())


def start(guide, form):
    info = guide.register_form(form.jsx, form.form_id, form.domain)
    return {"config": form.compute(None), "jsx_hash": info["jsx_hash"], "form_id": form.form_id, "ui": {}}


def test_full_flow_with_interrupt_and_ignored_card(guide, model):
    model.script = [
        say("", ("t1", "focus_field", {"name": "loan_type", "hint": "Start here"}),
            ("t2", "propose_changes", {"changes": [{"name": "loan_type", "value": "auto"},
                                                   {"name": "age", "value": "30"}]})),
        say("Done, the Collateral tab appeared."),
        say("", ("t3", "propose_changes", {"changes": [{"name": "loan_amount", "value": "900 000"}]})),
        say("Ok."),
    ]
    state = start(guide, LOAN)
    ev = collect(guide, "th", message="I want a car loan", state=state)
    names = [e.get("name") or e["type"] for e in ev]
    assert "agent_context" in names and "ui_directive" in names and "on_interrupt" in names
    directive = next(e["value"] for e in ev if e.get("name") == "ui_directive")
    assert directive["reveal"] == [{"type": "tab", "tabs": "main", "tab": "tab_loan"},
                                   {"type": "accordion", "name": "acc_loan_params"}]
    intr = next(json.loads(e["value"]) for e in ev if e.get("name") == "on_interrupt")
    assert [x["name"] for x in intr["changes"]] == ["loan_type"]            # age (🔒) dropped by validation
    assert intr["changes"][0]["value"] == {"id": "auto", "name": "Car loan"}

    new_cfg = LOAN.compute({**state["config"]["state"], "loan_type": intr["changes"][0]["value"]})
    ev = collect(guide, "th", resume={"accepted": True, "config": new_cfg})
    assert any(e["type"] == "TEXT_MESSAGE_CONTENT" for e in ev)
    results = {m.tool_call_id: m for m in model.calls[1] if isinstance(m, ToolMessage)}
    assert "tab_collateral" in results["t2"].content and "age is read-only" in results["t2"].content

    state2 = {**state, "config": new_cfg}
    ev = collect(guide, "th", message="the amount is 900k", state=state2)
    assert any(e.get("name") == "on_interrupt" for e in ev)
    collect(guide, "th", message="where is the tax ID?", state=state2)                 # card ignored
    last = model.calls[3]
    tool_msg = [m for m in last if isinstance(m, ToolMessage) and m.tool_call_id == "t3"]
    assert tool_msg and "did not answer the card" in tool_msg[0].content
    assert isinstance(last[-1], HumanMessage) and "CHANGES" in last[-1].content[0]["text"]


def test_tools_are_provider_neutral_and_include_skill_tools(guide, model):
    model.script = [say("hi")]
    collect(guide, "t", message="hello", state=start(guide, BARBER))
    names = [t["function"]["name"] if isinstance(t, dict) else t.name for t in model.bound]
    assert {"propose_changes", "use_skill", "check_gift_card"} <= set(names)
    assert "ask_documents" not in names                    # auto: the barber form has no documents here
    collect(guide, "t2", message="hello", state=start(guide, LOAN))
    names = [t["function"]["name"] if isinstance(t, dict) else t.name for t in model.bound]
    assert "check_gift_card" not in names                                    # skill scoped to the barber form
    system = model.calls[-1][0].content
    assert "income_proof" in system and "gift_cards" not in system


def test_skill_instructions_and_skill_tool_run(guide, model):
    model.script = [
        say("", ("s1", "use_skill", {"name": "gift_cards"})),
        say("", ("s2", "check_gift_card", {"code": "gc-1234-5678"})),
        say("Your card has $50."),
    ]
    collect(guide, "g", message="I have a gift card GC-1234-5678", state=start(guide, BARBER))
    tool_msgs = [m for call in model.calls for m in call if isinstance(m, ToolMessage)]
    by_id = {m.tool_call_id: m.content for m in tool_msgs}
    assert "check_gift_card" in by_id["s1"] and "balance $50" in by_id["s2"]


def test_gated_tab_blocks_changes_and_explains(guide):
    from formguide.form.layout import LayoutIndex
    lay = LayoutIndex(LOAN.jsx)
    ov = Overlay(lay, LOAN.compute({"loan_type": {"id": "mortgage", "name": "Mortgage"}}))
    ctx = ToolCtx(ov=ov, deps=DepStore(), pack=guide.packs.get("loan_application"), loc=locate(ov, {}), guide=guide)
    assert ov["consent_pd"].disabled and not ov["consent_pd"].own_disabled
    with pytest.raises(ToolError) as e:
        asyncio.run(run_tool("propose_changes", {"changes": [{"name": "consent_pd", "value": True}]}, ctx))
    assert "tab_documents" in str(e.value) and "GUESS" in str(e.value)


def test_note_detection():
    hello_ru = "\u041f\u0440\u0438\u0432\u0435\u0442"          # a Cyrillic greeting
    done_ru = "\u0413\u043e\u0442\u043e\u0432\u043e."           # "Done." in Cyrillic
    assert is_note("Need field names.", {"tool_round": 0, "user_text": hello_ru})
    assert is_note("Need field names.", {"tool_round": 2, "user_text": hello_ru})   # other script than the user
    assert not is_note(done_ru, {"tool_round": 2, "user_text": hello_ru})
    assert not is_note("Booked for 3pm.", {"tool_round": 2, "user_text": "Book me a haircut"})


def test_http_router(guide, model):
    app = FastAPI()
    app.include_router(create_router(guide), prefix="/agent")
    c = TestClient(app)
    r = c.post("/agent/layouts", json={"jsx": BARBER.jsx, "form_id": "barber_booking", "domain": BARBER.domain}).json()
    assert r["domain_pack"] == "inline" and not r["warnings"]
    model.script = [say("Hello!")]
    body = {"threadId": "h", "messages": [{"role": "user", "content": "hi"}],
            "state": {"config": BARBER.compute(None), "jsx_hash": r["jsx_hash"], "form_id": "barber_booking"}}
    text = c.post("/agent/run", json=body).text
    assert "TEXT_MESSAGE_CONTENT" in text and "Hello!" in text
    assert c.post("/agent/run", json={**body, "state": {"jsx_hash": "nope"}}).status_code == 409


# ===================================================================== long chats and reasoning blocks


def _system_text(call) -> str:
    c = call[0].content
    return c if isinstance(c, str) else c[0]["text"]


def test_system_prompt_frozen_and_updates_appended(guide, model):
    model.script = [say("one"), say("two")]
    state = start(guide, BARBER)
    collect(guide, "f", message="hi", state=state)
    guide.knowledge.add_document("barber_booking", "rules.md", b"# Rules\n\nNo pets.")
    guide.knowledge.save_compiled("barber_booking", {"rules": ["No pets in the salon (rules.md)"], "field_notes": {}})
    collect(guide, "f", message="again", state=state)
    assert _system_text(model.calls[0]) == _system_text(model.calls[1])       # never edited mid-thread
    last_user = model.calls[1][-1].content
    assert "<updated_instructions>" in last_user[0]["text"] and "No pets" in last_user[0]["text"]
    model.script = [say("three")]
    collect(guide, "f", message="and again", state=state)
    texts = [b["text"] for b in model.calls[-1][-1].content if isinstance(b, dict)]
    assert not any("<updated_instructions>" in t for t in texts)                  # delivered once per change


def test_retry_without_reasoning_blocks(guide, model):
    from langchain_core.messages import AIMessage

    class BindingError(Exception):
        pass

    calls = {"n": 0}
    real = model._stream

    def flaky(messages, *a, **k):
        calls["n"] += 1
        if calls["n"] == 2 and any(isinstance(m, AIMessage) and isinstance(m.content, list)
                                   and any(b.get("type") == "thinking" for b in m.content) for m in messages):
            raise BindingError("Invalid `signature` in `thinking` block. The block is bound to a different conversation.")
        return real(messages, *a, **k)

    object.__setattr__(model, "_stream", flaky)
    model.script = [AIMessage(content=[{"type": "thinking", "thinking": "", "signature": "x"},
                                       {"type": "text", "text": "first"}]), say("second")]
    state = start(guide, BARBER)
    collect(guide, "r", message="hi", state=state)
    ev = collect(guide, "r", message="again", state=state)
    assert not any(e["type"] == "RUN_ERROR" for e in ev) and calls["n"] == 3
    sent = model.calls[-1]
    assert not any(isinstance(m, AIMessage) and isinstance(m.content, list)
                   and any(b.get("type") == "thinking" for b in m.content) for m in sent)


def test_compaction_keeps_recent_turns_and_memory(guide, model):
    guide.config.memory.max_history_tokens = 200
    guide.config.memory.keep_turns = 1
    model.script = [say("Noted, I'll enter the code word once the tab unlocks."), say("ok")]
    state = start(guide, LOAN)
    collect(guide, "m", message="The code word is Barsik, enter it later", state=state)
    model.script = ["MEMORY", say("Sure.")]
    model.script[0] = say("## Facts the user gave\n- code word: Barsik (codeword) — NOT YET IN FORM: tab locked")
    ev = collect(guide, "m", message="what next?", state=state)
    assert any(e.get("name") == "memory_compacted" for e in ev)
    sent = model.calls[-1]
    humans = [m for m in sent if isinstance(m, HumanMessage)]
    assert len(humans) == 1                                                   # older turn replaced by memory
    first_block = humans[0].content[0]["text"]
    assert first_block.startswith("<conversation_memory>") and "Barsik" in first_block
    assert guide.graph.get_state({"configurable": {"thread_id": "m"}}).values["memory"].startswith("## Facts")


def test_focus_field_highlights_several_fields_of_a_section(guide):
    from formguide.form.layout import LayoutIndex
    lay = LayoutIndex(LOAN.jsx)
    ov = Overlay(lay, LOAN.compute({}))
    ctx = ToolCtx(ov=ov, deps=DepStore(), pack=guide.packs.get("loan_application"), loc=locate(ov, {}), guide=guide)
    out = asyncio.run(run_tool("focus_field", {"name": "acc_personal", "hint": "Required here",
                                               "fields": ["last_name", "first_name", "loan_amount", "nope"]}, ctx))
    d = ctx.ui_directives[-1]
    assert d["target"] == "acc_personal" and d["also"] == ["last_name", "first_name"]
    assert "also highlighted: last_name, first_name" in out and "loan_amount, nope" in out   # another section, unknown
