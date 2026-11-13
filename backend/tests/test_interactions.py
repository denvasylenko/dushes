"""Richer interactions: previous values, edits on the card, typed inputs, upload requests, confirmations,
tools that need a confirmation, tool progress, quick replies and starters."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from demo.mock_forms import FORMS
from formguide.agent import tools as T

from .conftest import say
from .test_agent import collect, start
from .test_agui import check_order

LOAN = FORMS["loan_application"]
LOAN_PACK = Path(__file__).resolve().parents[1] / "demo" / "domain_packs" / "loan_application.json"


def interrupt_value(ev):
    found = [e for e in ev if e.get("name") == "on_interrupt"]
    return json.loads(found[0]["value"]) if found else None


def result(model, call_id):
    return next(m.content for m in model.calls[-1] if isinstance(m, ToolMessage) and m.tool_call_id == call_id)


def pause(guide, model, thread, name, args, state=None):
    model.script = [say("", ("t1", name, args))]
    ev = collect(guide, thread, message="go", state=state or start(guide, LOAN))
    check_order(ev)
    return interrupt_value(ev), ev


# ---------------------------------------------------------------- field changes


def test_previous_values_and_edits(guide, model):
    state = start(guide, LOAN)
    state["config"]["state"]["first_name"] = "Ana"
    v, _ = pause(guide, model, "e1", "propose_changes",
                 {"changes": [{"name": "first_name", "value": "Anna"}, {"name": "last_name", "value": "Ivanova"}]},
                 state)
    by = {c["name"]: c for c in v["changes"]}
    assert by["first_name"]["previous"] == "Ana" and by["first_name"]["previous_display"] == "Ana"
    assert by["last_name"]["previous"] is None and by["last_name"]["previous_display"] is None

    model.script = [say("Done.")]
    collect(guide, "e1", resume={"accepted": True, "config": state["config"],
                                 "edited": {"last_name": "Petrova", "first_name": "Anna", "nope": 1}})
    text = result(model, "t1")
    assert 'The user edited before applying: last_name -> "Petrova".' in text
    card = next(e for e in guide.thread("e1")["transcript"] if e["kind"] == "card")
    assert card["edited"] == {"last_name": "Petrova"}


def test_prefill_values_carry_previous(guide):
    state = start(guide, LOAN)
    state["config"]["state"]["first_name"] = "Ana"
    res = asyncio.run(guide.suggest_prefill(state, data={"first_name": "Anna"}))
    assert res["values"][0]["previous"] == "Ana"


# ---------------------------------------------------------------- typed inputs


def test_question_with_a_date_input(guide, model):
    q = {"question": "When?", "input": {"type": "date", "min": "2026-11-12"}}
    v, _ = pause(guide, model, "d1", "ask_user", q)
    assert v["input"] == {"type": "date", "min": "2026-11-12"} and v["allow_text"] is True
    for thread, text, expected in [("d1", "2026-11-20", "The user wrote: 2026-11-20"),
                                   ("d2", "2026-11-01", "out of range"),
                                   ("d3", "next week", "is not YYYY-MM-DD")]:
        if thread != "d1":
            pause(guide, model, thread, "ask_user", q)
        model.script = [say("Ok.")]
        collect(guide, thread, resume={"answer": {"text": text}})
        assert expected in result(model, "t1"), thread


def test_question_input_from_a_date_field_and_bad_bounds(guide, model):
    v, _ = pause(guide, model, "d4", "ask_user", {"question": "Your birth date?", "field": "birth_date"})
    assert v["input"]["type"] == "date" and v["options"] == []
    assert v["input"]["max"]   # a date of birth is in the past
    model.script = [say("", ("t1", "ask_user", {"question": "?", "input": {"type": "date", "min": "soon"}})),
                    say("Ok.")]
    collect(guide, "d5", message="go", state=start(guide, LOAN))
    assert "is not a valid date" in result(model, "t1")


# ---------------------------------------------------------------- upload requests


def test_request_file(guide, model):
    v, _ = pause(guide, model, "u1", "request_file", {"prompt": "Upload your passport", "accept": "pdf, .jpg, .exe"})
    assert v["type"] == "upload" and v["accept"] == ".pdf,.jpg" and v["multiple"] is False
    assert guide.thread("u1")["pending_card"]["kind"] == "upload"
    att = guide.save_attachment("u1", "passport.pdf", b"%PDF-1.4 test")
    model.script = [say("Reading it.")]
    collect(guide, "u1", resume={"attachment_ids": [att["id"], "att_00000000"]})
    text = result(model, "t1")
    assert f"passport.pdf (attachment_id={att['id']})" in text and "att_00000000" not in text
    entry = next(e for e in guide.thread("u1")["transcript"] if e["kind"] == "upload")
    assert entry["status"] == "answered" and entry["files"][0]["filename"] == "passport.pdf"

    pause(guide, model, "u2", "request_file", {"prompt": "Upload a payslip"})
    model.script = [say("Ok.")]
    collect(guide, "u2", resume={"accepted": False})
    assert "did not upload" in result(model, "t1")
    assert next(e for e in guide.thread("u2")["transcript"] if e["kind"] == "upload")["status"] == "dismissed"


# ---------------------------------------------------------------- confirmations


def test_confirm_action(guide, model):
    v, ev = pause(guide, model, "c1", "confirm_action",
                  {"title": "Submit the application?", "message": "It goes to the bank.", "danger": True})
    assert v["type"] == "confirm" and v["danger"] is True and v["title"] == "Submit the application?"
    model.script = [say("Submitting.")]
    collect(guide, "c1", resume={"accepted": True})
    assert result(model, "t1") == "The user confirmed."
    assert next(e for e in guide.thread("c1")["transcript"] if e["kind"] == "confirm")["status"] == "accepted"

    guide.config.interrupt_mode = "structured"
    _, ev = pause(guide, model, "c2", "confirm_action", {"title": "Cancel?", "message": "The booking is cancelled."})
    out = ev[-1]["outcome"]["interrupts"][0]
    assert out["reason"] == "confirm_action" and out["message"] == "Cancel?"
    model.script = [say("Ok.")]
    collect(guide, "c2", resume={"accepted": False})
    assert result(model, "t1") == "The user declined."


def test_confirm_tools_hold_the_call(guide, model):
    ran = []

    @tool
    def submit_application(reference: str) -> str:
        """Submit the application to the bank."""
        ran.append(reference)
        return f"submitted {reference}"

    guide._tools.append(submit_application)
    guide.config.confirm_tools = ["submit_application"]
    v, _ = pause(guide, model, "h1", "submit_application", {"reference": "A-1"})
    assert v["type"] == "confirm" and v["tool"] == "submit_application" and "reference: A-1" in v["message"]
    assert not ran
    model.script = [say("Done.")]
    collect(guide, "h1", resume={"accepted": True})
    assert ran == ["A-1"] and result(model, "t1") == "The user confirmed. submitted A-1"

    pause(guide, model, "h2", "submit_application", {"reference": "A-2"})
    model.script = [say("Ok.")]
    collect(guide, "h2", resume={"accepted": False})
    assert ran == ["A-1"] and result(model, "t1") == "The user declined; the tool was not run."


# ---------------------------------------------------------------- progress, suggestions, starters


def test_tool_progress_events(guide, model, monkeypatch):
    def _t_fake_research(a, ctx):
        ctx.emit({"kind": "tool", "name": "docs.search", "input": {"q": "rate"}})
        ctx.emit({"kind": "tool", "name": "docs.read", "input": {"doc": "rules.md"}})
        return "found it"

    monkeypatch.setattr(T, "TOOLS", T.TOOLS + [{"name": "fake_research", "description": "x",
                                                "input_schema": {"type": "object", "properties": {}}}])
    monkeypatch.setattr(T, "BUILTIN", T.BUILTIN | {"fake_research"})
    monkeypatch.setattr(T, "_t_fake_research", _t_fake_research, raising=False)
    model.script = [say("", ("r1", "fake_research", {})), say("Here it is.")]
    ev = collect(guide, "p1", message="what is the rate?", state=start(guide, LOAN))
    check_order(ev)
    prog = [e["value"] for e in ev if e.get("name") == "tool_progress"]
    assert [p["name"] for p in prog] == ["docs.search", "docs.read"] and {p["parent_id"] for p in prog} == {"r1"}
    order = [e["type"] if e["type"] != "CUSTOM" else e["name"] for e in ev]
    assert order.index("TOOL_CALL_END") < order.index("tool_progress") < order.index("TOOL_CALL_RESULT")


def test_suggestions(guide, model):
    model.script = [say("The Loan tab is open now."), say('{"items": ["How much can I borrow?", "What next?"]}')]
    ev = collect(guide, "s1", message="hi", state=start(guide, LOAN))
    assert not any(e.get("name") == "suggestions" for e in ev)       # disabled by default

    guide.config.suggestions.enabled = True
    guide.suggestions_model = model
    model.script = [say("The Loan tab is open now."), say('```json\n{"items": ["How much can I borrow?", "What next?"]}\n```')]
    ev = collect(guide, "s2", message="hi", state=start(guide, LOAN))
    check_order(ev)
    sug = [e for e in ev if e.get("name") == "suggestions"]
    assert sug[0]["value"]["items"] == ["How much can I borrow?", "What next?"]
    assert [e["type"] for e in ev][-2:] == ["CUSTOM", "RUN_FINISHED"]

    model.script = [say("", ("t1", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]}))]
    ev = collect(guide, "s3", message="I am Anna", state=start(guide, LOAN))
    assert not any(e.get("name") == "suggestions" for e in ev)       # not after a card

    class Slow:
        async def ainvoke(self, msgs):
            await asyncio.sleep(1)

    guide.suggestions_model, guide.config.suggestions.timeout = Slow(), 0.05
    model.script = [say("Hello.")]
    ev = collect(guide, "s4", message="hi", state=start(guide, LOAN))
    assert ev[-1]["type"] == "RUN_FINISHED" and not any(e.get("name") == "suggestions" for e in ev)


def test_starters_and_config(guide, tmp_path):
    from formguide.config import load_config
    from formguide.domain.packs import DomainPack, validate_pack

    guide.packs.register("loan_application", {**json.loads((LOAN_PACK).read_text()),
                                               "starters": ["Where do I start?", "What documents do I need?"]})
    assert guide.thread("new-thread", "loan_application")["starters"] == ["Where do I start?",
                                                                          "What documents do I need?"]
    assert "starters" not in guide.thread("new-thread")
    w = validate_pack(DomainPack(form_id="x", starters=["a"] * 7 + [3]), set())
    assert any("at most 6" in x for x in w) and any("non-empty strings" in x for x in w)

    f = tmp_path / "formguide.yaml"
    f.write_text("model: {class: \"tests.conftest:ScriptedChatModel\"}\nconfirm_tools: [submit_application]\n"
                 "suggestions: {max: 9, timeout: 2}\n")
    cfg = load_config(f)
    assert cfg.confirm_tools == ["submit_application"]
    assert cfg.suggestions.enabled is True and cfg.suggestions.max == 5 and cfg.suggestions.timeout == 2.0


def test_suggestions_with_changes(guide, model):
    guide.config.suggestions.enabled = True
    guide.suggestions_model = model
    reply = json.dumps({"items": [{"text": "Make it a car loan", "set": {"loan_type": "auto"}},
                                  {"text": "Bad pick", "set": {"loan_type": "spaceship", "nope": 1}},
                                  "What next?"]})
    model.script = [say("A car loan fits."), say(reply)]
    ev = collect(guide, "sc1", message="I need a car", state=start(guide, LOAN))
    sug = next(e["value"] for e in ev if e.get("name") == "suggestions")
    assert sug["items"] == ["Make it a car loan", "Bad pick", "What next?"]
    first, bad, plain = sug["applies"]
    assert [c["name"] for c in first] == ["loan_type"] and first[0]["display"] and "previous" in first[0]
    assert any(r["type"] == "tab" for r in first[0]["reveal"])   # where the chip's field is
    assert bad is None and plain is None          # an invalid value drops the changes, keeps the text

    state = start(guide, LOAN)
    state["config"]["state"]["loan_type"] = first[0]["value"]       # already set: that chip is not offered
    model.script = [say("Done."), say(reply)]
    ev = collect(guide, "sc3", message="ok", state=state)
    assert next(e["value"] for e in ev if e.get("name") == "suggestions")["items"] == ["Bad pick", "What next?"]

    model.script = [say("Hello."), say('{"items": ["What next?"]}')]
    ev = collect(guide, "sc2", message="hi", state=start(guide, LOAN))
    assert "applies" not in next(e["value"] for e in ev if e.get("name") == "suggestions")


def test_dependent_field_is_deferred(guide, model):
    v, _ = pause(guide, model, "d1", "propose_changes",
                 {"changes": [{"name": "loan_purpose", "value": "Used car"}, {"name": "loan_type", "value": "auto"}]})
    names = [c["name"] for c in v["changes"]]
    assert names == ["loan_type", "loan_purpose"]          # the deferred row comes last
    later = v["changes"][1]
    assert later["deferred"] is True and later["value"] is None and later["lookup"] == "Used car"
    assert later["after"] == ["loan_type"] and later["display"] == "Used car" and later["shape"]

    model.script = [say("", ("t2", "propose_changes", {"changes": [{"name": "loan_purpose", "value": "Used car"}]})),
                    say("The purpose opens after the loan type.")]
    ev = collect(guide, "d2", message="used car", state=start(guide, LOAN))
    assert interrupt_value(ev) is None                      # nothing to wait for: an error, as before
    assert "loan_purpose" in result(model, "t2")


def test_card_keeps_its_lead_sentence(guide, model):
    model.script = [say("Here are the first fields.", ("t1", "propose_changes",
                                                       {"changes": [{"name": "first_name", "value": "Anna"}]}))]
    ev = collect(guide, "lead1", message="I am Anna", state=start(guide, LOAN))
    shown = "".join(e.get("delta", "") for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert shown == "Here are the first fields." and interrupt_value(ev) is not None

    model.script = [say("Need field names.", ("t2", "get_outline", {})), say("Hello.")]
    ev = collect(guide, "lead2", message="hi", state=start(guide, LOAN))
    shown = "".join(e.get("delta", "") for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "Need field names" not in shown                     # other tools: still an internal note
