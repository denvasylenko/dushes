"""The public researcher demo: sets, one run as the chat widget draws it, sources with their passage, the limits."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from docs_ai import host, research_demo

DOC = (b"# Tariffs 2026\n\n## Fees\n\nThe late fee is 27,90 EUR after the reminder. The monthly fee is 12,50 EUR.\n\n"
       b"## Limits\n\nA loan is up to 5 million.\n")


@pytest.fixture
def demo(tmp_path, monkeypatch):
    (tmp_path / "bank_tariffs").mkdir()
    (tmp_path / "bank_tariffs" / "tariffs_2026.md").write_bytes(DOC)
    (tmp_path / "bank_tariffs" / "README.md").write_text("not a document of the set")
    monkeypatch.setenv("RESEARCH_DEMO_DIR", str(tmp_path))
    from formguide.knowledge.base import KnowledgeBase
    monkeypatch.setattr(host.guide, "knowledge", KnowledgeBase(tmp_path / "kb"))
    for k, v in {"TABLE": {}, "PRICES": None}.items():
        monkeypatch.setattr(host, k, v)
    host._threads.clear()
    host._day = host.Day("")
    asked = {}

    async def fake(kb, scope, title, question, model, on_step=None, usage=None):
        asked.update(scope=scope, title=title, question=question, model=model)
        on_step("search_documents", {"query": "late fee"})
        on_step("read_section", {"section_id": "x#1"})
        if usage is not None:
            usage.append({"input_tokens": 900, "output_tokens": 60})
        return "A late payment costs 27,90 EUR once the reminder has gone out.\nSources: tariffs_2026.md > Fees"

    from formguide.knowledge import research
    monkeypatch.setattr(research, "ask_documents", fake)
    return asked


def _body(question="What is the late fee?", set_id="bank_tariffs", **fwd):
    return {"threadId": "rd1", "runId": "r1", "state": {"set": set_id}, "tools": [], "context": [],
            "messages": [{"id": "m1", "role": "user", "content": question}], "forwardedProps": fwd}


def _events(r):
    return [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]


def test_the_sets_are_listed(demo):
    with TestClient(host.app) as c:
        got = c.get("/research/sets").json()
    assert got["depths"] == ["auto", "quick", "deep"] and got["deeper"] == "Look deeper"
    (one,) = got["sets"]
    assert one["id"] == "bank_tariffs" and [d["title"] for d in one["documents"]] == ["tariffs_2026.md"]


def test_a_question_is_answered_with_steps_and_sources(demo):
    with TestClient(host.app) as c:
        r = c.post("/research/run", json=_body(depth="deep"), headers={"Accept": "text/event-stream"})
    assert r.status_code == 200
    ev = _events(r)
    assert ev[0]["type"] == "RUN_STARTED" and ev[-1]["type"] == "RUN_FINISHED"
    decide = next(e["value"] for e in ev if e.get("name") == "research")
    assert decide == {"phase": "decide", "depth": "deep", "asked": "deep", "why": "chosen"}
    assert [e["toolCallName"] for e in ev if e["type"] == "TOOL_CALL_START"] == ["docs.search_documents", "docs.read_section"]
    text = "".join(e["delta"] for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert text == "A late payment costs 27,90 EUR once the reminder has gone out."   # the chips carry the sources
    (src,) = next(e["value"]["items"] for e in ev if e.get("name") == "sources")
    assert src["title"] == "tariffs_2026.md" and src["section"] == "Fees"
    ((start, end),) = src["marks"]
    assert src["excerpt"][start:end].strip() == "The late fee is 27,90 EUR after the reminder."
    stats = next(e["value"] for e in ev if e.get("name") == "run_stats")
    assert stats["agent"] == "research" and stats["models"][0]["kind"] == "researcher"
    assert demo["scope"] == "research_bank_tariffs" and demo["question"] == "What is the late fee?"
    assert host.guide.knowledge.list_documents("research_bank_tariffs")[0]["filename"] == "tariffs_2026.md"


def test_what_is_refused(demo):
    with TestClient(host.app) as c:
        assert c.post("/research/run", json=_body(set_id="nope")).status_code == 422
        assert c.post("/research/run", json=_body(depth="deepest")).status_code == 422
        assert c.post("/research/run", json=_body(question="")).status_code == 400
        assert c.post("/research/run", json=_body(question="x" * 700)).status_code == 413
        assert c.post("/research/run", json=_body(model="gpt-9")).status_code == 422
        assert c.post("/research/kb/bank_tariffs/documents").status_code in (404, 405)   # no uploads here


def test_the_demo_limits_apply(demo, monkeypatch):
    monkeypatch.setattr(host, "PER_THREAD", 1)
    with TestClient(host.app) as c:
        assert c.post("/research/run", json=_body()).status_code == 200
        r = c.post("/research/run", json=_body())
    assert r.status_code == 429 and r.json()["reason"] == "thread"



def test_depth_is_chosen_by_the_questions_wording():
    assert research_demo.decide("auto", "What is the late fee?") == ("quick", "a plain question")
    assert research_demo.decide("auto", "Compare the two tariffs")[0] == "deep"
    assert research_demo.decide("auto", "Why is the Plus tariff dearer? Explain in detail")[0] == "deep"
    assert research_demo.decide("quick", "Compare the two tariffs") == ("quick", "chosen")
    assert research_demo.decide("deep", "What is the late fee?") == ("deep", "chosen")


def test_a_quick_answer_is_one_search_and_one_model_call(demo, monkeypatch):
    from langchain_core.messages import AIMessage

    from .conftest import ScriptedChatModel
    quick = ScriptedChatModel(script=[AIMessage(content="A late payment costs 27,90 EUR after the reminder [1].")])
    monkeypatch.setattr(host.guide._default.models, "research", quick)
    with TestClient(host.app) as c:
        r = c.post("/research/run", json=_body(), headers={"Accept": "text/event-stream"})      # depth auto
        ev = _events(r)
        assert next(e["value"] for e in ev if e.get("name") == "research")["depth"] == "quick"
        assert len(quick.calls) == 1 and "scope" not in demo                 # the researcher's loop did not run
        assert "[1] tariffs_2026.md > " in quick.calls[0][1].content and "27,90" in quick.calls[0][1].content
        assert [e["toolCallName"] for e in ev if e["type"] == "TOOL_CALL_START"] == ["docs.search_documents"]
        (src,) = next(e["value"]["items"] for e in ev if e.get("name") == "sources")
        ((start, end),) = src["marks"]
        assert src["n"] == 1 and "27,90" in src["excerpt"][start:end]
        assert next(e["value"]["items"] for e in ev if e.get("name") == "suggestions") == ["Look deeper"]
        assert ev[-1]["type"] == "RUN_FINISHED"
        # the tap: the same question, by the researcher
        body = _body()
        body["messages"] = [{"id": "m1", "role": "user", "content": "What is the late fee?"},
                            {"id": "m2", "role": "assistant", "content": "A late payment costs 27,90 EUR [1]."},
                            {"id": "m3", "role": "user", "content": "Look deeper"}]
        body["threadId"] = "rd2"
        ev = _events(c.post("/research/run", json=body))
        assert next(e["value"] for e in ev if e.get("name") == "research")["depth"] == "deep"
        assert demo["question"] == "What is the late fee?"


def test_a_quick_look_that_finds_nothing_says_so(demo, monkeypatch):
    from .conftest import ScriptedChatModel
    quick = ScriptedChatModel()
    monkeypatch.setattr(host.guide._default.models, "research", quick)
    with TestClient(host.app) as c:
        ev = _events(c.post("/research/run", json=_body(question="zzzqqq xyzzy?", depth="quick")))
    text = "".join(e["delta"] for e in ev if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert "found nothing" in text and not quick.calls and not any(e.get("name") == "sources" for e in ev)
    assert next(e["value"]["items"] for e in ev if e.get("name") == "suggestions") == ["Look deeper"]


def test_only_the_public_sets_are_offered_from_the_shipped_corpora(monkeypatch):
    monkeypatch.delenv("RESEARCH_DEMO_DIR", raising=False)
    assert research_demo.set_ids() == ["halden_policies", "orrin_catalogue", "tessel_contract", "veltra_manual"]
    assert research_demo.set_name("orrin_catalogue") == "Product catalogue (Orrin Tools)"

