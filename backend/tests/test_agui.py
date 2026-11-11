"""AG-UI protocol: event order, interrupt channels, resume forms, frontend tools, export, prefill."""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import ToolMessage

from demo.mock_forms import FORMS
from formguide import agui
from formguide.server import create_router

from .conftest import say
from .test_agent import collect, start

LOAN = FORMS["loan_application"]


def types(ev):
    return [e["type"] for e in ev]


def check_order(ev):
    """The AG-UI rules a client verifies: one start, one terminal event, balanced messages and tool calls."""
    t = types(ev)
    assert t[0] == "RUN_STARTED" and t[-1] in ("RUN_FINISHED", "RUN_ERROR")
    assert t.count("RUN_FINISHED") + t.count("RUN_ERROR") == 1
    open_text, open_calls = set(), set()
    for e in ev:
        if e["type"] == "TEXT_MESSAGE_START":
            open_text.add(e["messageId"])
        elif e["type"] in ("TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"):
            assert e["messageId"] in open_text
            if e["type"] == "TEXT_MESSAGE_END":
                open_text.discard(e["messageId"])
        elif e["type"] == "TOOL_CALL_START":
            open_calls.add(e["toolCallId"])
        elif e["type"] in ("TOOL_CALL_ARGS", "TOOL_CALL_END"):
            assert e["toolCallId"] in open_calls
            if e["type"] == "TOOL_CALL_END":
                open_calls.discard(e["toolCallId"])
    assert not open_text and not open_calls
    for e in ev:   # every event is valid for the official models
        agui._EVENT.validate_python(e)


def test_server_tools_stream_as_tool_calls_with_results(guide, model):
    model.script = [say("", ("t1", "get_outline", {})), say("Here is the form.")]
    ev = collect(guide, "a1", message="what is in the form?", state=start(guide, LOAN))
    check_order(ev)
    t = types(ev)
    i = t.index("TOOL_CALL_START")
    assert t[i:i + 4] == ["TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END", "TOOL_CALL_RESULT"]
    res = next(e for e in ev if e["type"] == "TOOL_CALL_RESULT")
    assert res["toolCallId"] == "t1" and res["content"]
    tool = next(e for e in guide.thread("a1")["transcript"] if e["kind"] == "tool")
    assert tool["call_id"] == "t1" and tool["result"] == res["content"]


def test_legacy_interrupt_is_a_json_string_and_structured_outcome(guide, model):
    model.script = [say("", ("t1", "propose_changes", {"changes": [{"name": "loan_type", "value": "auto"}]}))]
    ev = collect(guide, "a2", message="car loan", state=start(guide, LOAN))
    check_order(ev)
    value = json.loads(next(e for e in ev if e.get("name") == "on_interrupt")["value"])
    assert value["type"] == "set_fields" and value["card_id"] and value["changes"][0]["name"] == "loan_type"
    assert "outcome" not in ev[-1]

    guide.config.interrupt_mode = "structured"
    model.script = [say("", ("t2", "propose_changes", {"changes": [{"name": "loan_type", "value": "auto"}]}))]
    ev = collect(guide, "a3", message="car loan", state=start(guide, LOAN))
    check_order(ev)
    assert not any(e.get("name") == "on_interrupt" for e in ev)
    out = ev[-1]["outcome"]
    assert out["type"] == "interrupt" and out["interrupts"][0]["reason"] == "confirm_field_changes"
    assert out["interrupts"][0]["id"] == guide.thread("a3")["pending_card"]["id"]


def test_resume_forms():
    base = {"threadId": "x", "runId": "r", "messages": [{"id": "1", "role": "user", "content": "hi"}]}
    assert agui.run_kwargs({**base, "resume": [{"interrupt_id": "c", "status": "cancelled"}]})["resume"] == {
        "accepted": False}
    kw = agui.run_kwargs({**base, "resume": [{"interrupt_id": "c", "status": "resolved",
                                              "payload": {"accepted": True, "config": {"a": 1}}}]})
    assert kw["resume"] == {"accepted": True, "config": {"a": 1}} and kw["message"] is None
    kw = agui.run_kwargs({**base, "forwardedProps": {"command": {"resume": json.dumps({"accepted": False})}}})
    assert kw["resume"] == {"accepted": False}
    kw = agui.run_kwargs({"threadId": "x", "messages": [{"role": "user", "content": [
        {"type": "text", "text": "hello"}]}]})
    assert kw["message"] == "hello" and kw["run_id"]
    kw = agui.run_kwargs({**base, "messages": base["messages"] + [{"id": "2", "role": "assistant", "content": "hey"}],
                          "forwardedProps": {"prefill": {"data": {"a": 1}}}})
    assert kw["message"] is None and kw["prefill"] == {"data": {"a": 1}}


def test_provider_error_ends_with_run_error(guide, model):
    model.script = [RuntimeError("provider is down")]
    ev = collect(guide, "a4", message="hi", state=start(guide, LOAN))
    check_order(ev)
    assert ev[-1]["type"] == "RUN_ERROR" and "RUN_FINISHED" not in types(ev)


def test_frontend_tools_round_trip(guide, model):
    tools = [{"name": "highlightField", "description": "Flash a field in the UI",
              "parameters": {"type": "object", "properties": {"name": {"type": "string"}}}},
             {"name": "get_outline", "description": "client tool trying to shadow a built-in"}]
    model.script = [say("Let me show you.", ("c1", "highlightField", {"name": "email"}))]
    state = start(guide, LOAN)
    ev = collect(guide, "a5", message="where is email?", state=state, client_tools=tools)
    check_order(ev)
    names = [b["function"]["name"] if isinstance(b, dict) else b.name for b in model.bound]
    assert names.count("get_outline") == 1 and "highlightField" in names
    assert any(e["type"] == "TOOL_CALL_START" and e["toolCallName"] == "highlightField" for e in ev)
    assert not any(e["type"] == "TOOL_CALL_RESULT" for e in ev)        # the client runs it
    assert ev[-1]["type"] == "RUN_FINISHED"

    model.script = [say("It is highlighted now.")]
    ev = collect(guide, "a5", state=state, client_tools=tools, tool_results={"c1": "highlighted"})
    check_order(ev)
    sent = model.calls[-1]
    assert any(isinstance(m, ToolMessage) and m.tool_call_id == "c1" and m.content == "highlighted" for m in sent)
    tx = guide.thread("a5")["transcript"]
    assert [e["kind"] for e in tx] == ["user", "tool", "assistant"]   # no empty user entry for the continuation
    assert tx[1]["result"] == "highlighted"

    msgs = guide.thread_messages("a5")
    assert [m["role"] for m in msgs] == ["user", "assistant", "tool", "assistant"]
    assert msgs[1]["toolCalls"][0]["function"]["name"] == "highlightField"


def test_missing_frontend_result_is_reported(guide, model):
    tools = [{"name": "highlightField", "description": "Flash a field"}]
    model.script = [say("", ("c1", "highlightField", {}))]
    state = start(guide, LOAN)
    collect(guide, "a6", message="show me", state=state, client_tools=tools)
    model.script = [say("Ok.")]
    collect(guide, "a6", message="never mind", state=state, client_tools=tools)
    sent = model.calls[-1]
    assert any(isinstance(m, ToolMessage) and m.tool_call_id == "c1" and "did not run" in m.content for m in sent)


def test_suggest_prefill_direct_data(guide):
    import asyncio

    state = start(guide, LOAN)
    res = asyncio.run(guide.suggest_prefill(state, data={
        "first_name": "Anna", "gender": "Female", "consent_pd": True, "age": 30, "birth_date": "31.02.1990"}))
    by = {v["name"]: v for v in res["values"]}
    assert by["first_name"]["value"] == "Anna" and by["first_name"]["status"] == "now"
    assert by["gender"]["value"] == {"id": "f", "name": "Female"}
    assert by["consent_pd"]["status"] == "later"                       # inside a locked step
    assert any("age" in e for e in res["errors"]) and any("birth_date" in e for e in res["errors"])


def test_prefill_in_chat(guide, model):
    model.script = [say("", ("t1", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]})),
                    ]
    ev = collect(guide, "a7", state=start(guide, LOAN), prefill={"data": {"first_name": "Anna", "consent_pd": True}})
    check_order(ev)
    prompt = model.calls[-1][-1].content
    text = " ".join(b["text"] for b in prompt if b.get("type") == "text")
    assert "first_name" in text and "consent_pd" in text and "locked or hidden" in text
    kinds = [e["kind"] for e in guide.thread("a7")["transcript"]]
    assert kinds[0] == "notice" and "user" not in kinds and kinds[-1] == "card"


def test_router_agui_input_and_export(guide, model):
    app = FastAPI()
    app.include_router(create_router(guide), prefix="/agent")
    c = TestClient(app)
    state = start(guide, LOAN)
    model.script = [say("Hello!")]
    body = {"threadId": "a8", "runId": "r1", "state": state, "tools": [], "context": [], "forwardedProps": {},
            "messages": [{"id": "u1", "role": "user", "content": "hi"}]}
    r = c.post("/agent/run", json=body)
    assert r.headers["content-type"].startswith("text/event-stream")
    ev = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    check_order(ev)
    assert c.post("/agent/run", json={"threadId": 1}).status_code == 422
    msgs = c.get("/agent/threads/a8?format=agui").json()["messages"]
    assert [(m["role"], m["content"]) for m in msgs] == [("user", "hi"), ("assistant", "Hello!")]
    p = c.post("/agent/prefill", json={"state": state, "data": {"first_name": "Anna"}}).json()
    assert p["values"][0]["name"] == "first_name"


def test_cli_init_check_and_create_app(tmp_path, capsys):
    from formguide.app import create_app
    from formguide.cli import main

    assert main(["init", str(tmp_path / "agent")]) == 0
    cfg = tmp_path / "agent" / "formguide.yaml"
    assert cfg.exists() and (tmp_path / "agent" / "skills" / "example_skill" / "SKILL.md").exists()
    assert main(["check", "--config", str(cfg)]) == 0
    out = capsys.readouterr().out
    assert "my_form" in out and "example_skill" in out and out.strip().endswith("OK")
    cfg.write_text("model: {class: \"tests.conftest:ScriptedChatModel\"}\n")
    app = create_app(cfg, prefix="/x")
    assert TestClient(app).get("/x/health").json() == {"ok": True}
    assert type(app.state.guide.models.agent).__name__ == "ScriptedChatModel"


def test_layouts_survive_a_restart(tmp_path, model):
    from formguide import FormGuide, GuideConfig, Models

    g1 = FormGuide(GuideConfig(models=Models(agent=model), data_dir=tmp_path))
    h = g1.register_form(LOAN.jsx, LOAN.form_id)["jsx_hash"]
    g2 = FormGuide(GuideConfig(models=Models(agent=model), data_dir=tmp_path))
    assert g2.layout(h) is not None and g2.layout("../x") is None
