"""The public host (docs_ai.host): the docs assistant mounted next to the demo, and the demo's limits."""
from __future__ import annotations

from fastapi.testclient import TestClient

from docs_ai import host


def _fresh(monkeypatch, **limits):
    for k, v in limits.items():
        monkeypatch.setattr(host, k, v)
    host._threads.clear()
    host._day = host.Day("")


def _run(c, thread="t1", resume=False, visitor=None):
    body = {"threadId": thread, "runId": "r", "state": {}, "messages": [{"id": "m", "role": "user", "content": "hi"}],
            "tools": [], "context": [], "forwardedProps": {"command": {"resume": {"accepted": False}}} if resume else {}}
    return c.post("/agent/run", json=body, headers={"X-Demo-Visitor": visitor} if visitor else {})


def test_document_uploads_are_off():
    with TestClient(host.app) as c:
        assert c.post("/agent/kb/loan_application/documents").status_code == 403
        assert c.delete("/agent/kb/loan_application/documents/x").status_code == 403


def test_a_demo_chat_has_a_limit_and_card_answers_do_not_count(monkeypatch):
    _fresh(monkeypatch, PER_THREAD=2)
    monkeypatch.setitem(host.SENTENCES, "thread", "This demo chat has reached its 2 messages.")
    with TestClient(host.app) as c:
        codes = [_run(c, "lim").status_code for _ in range(2)]
        assert 429 not in codes
        assert _run(c, "lim", resume=True).status_code != 429   # answering a card is not a new message
        r = _run(c, "lim")
        assert r.status_code == 429 and "2 messages" in r.json()["detail"]
        assert r.json()["code"] == "demo_limit" and r.json()["reason"] == "thread" and r.json()["link"]


def test_the_docs_assistant_is_mounted():
    with TestClient(host.app) as c:
        assert c.get("/ai/health").status_code == 200


def test_the_site_demo_shares_the_limit(monkeypatch):
    _fresh(monkeypatch, PER_THREAD=1)
    body = {"threadId": "site1", "runId": "r", "state": {"page": {"path": "/"}}, "messages": [{"id": "m", "role": "user", "content": "hi"}],
            "tools": [], "context": [], "forwardedProps": {}}
    with TestClient(host.app) as c:
        assert c.post("/site/run", json=body).status_code != 429
        assert c.post("/site/run", json=body).status_code == 429
        assert c.get("/site/map").status_code == 200


def test_the_eleventh_message_of_a_visitor_is_refused(monkeypatch):
    _fresh(monkeypatch)
    with TestClient(host.app) as c:
        codes = [_run(c, f"v{i}", visitor="visitor-abc123").status_code for i in range(10)]
        assert 429 not in codes
        r = _run(c, "v10", visitor="visitor-abc123")
        assert r.status_code == 429 and r.json()["reason"] == "visitor"
        assert _run(c, "v11", visitor="visitor-xyz789").status_code != 429   # another visitor


def test_the_runs_of_a_day_are_capped(monkeypatch):
    _fresh(monkeypatch, RUNS_DAY=2)
    with TestClient(host.app) as c:
        assert _run(c, "r1").status_code != 429
        assert _run(c, "r1", resume=True).status_code != 429   # a card answer is a run too
        r = _run(c, "r2")
        assert r.status_code == 429 and r.json()["reason"] == "runs"


def test_the_cost_cap_comes_from_run_stats(monkeypatch):
    _fresh(monkeypatch, PRICES=host.prices("1,5,0.1,1.25"), COST_DAY=0.01)
    summary = {"models": [{"input_tokens": 5000, "output_tokens": 1000, "cache_read_tokens": 4000, "cache_write_tokens": 0}]}
    cost, tokens = host.run_cost(summary)
    assert round(cost, 6) == round(1000 * 1e-6 + 1000 * 5e-6 + 4000 * 0.1e-6, 6)   # cache reads are not plain input
    assert tokens["cache_read"] == 4000
    import json
    import logging
    with TestClient(host.app) as c:
        assert _run(c, "c1").status_code != 429
        logging.getLogger("formguide.stats").info(json.dumps({"models": [{"input_tokens": 2000, "output_tokens": 2000}]}))
        assert host.today().cost >= 0.01
        r = _run(c, "c2")
        assert r.status_code == 429 and r.json()["reason"] == "cost"
    day = json.loads((host.COUNTERS / f"{host.today().date}.json").read_text())
    assert day["runs"] == 1 and day["tokens"]["output"] == 2000 and "messages" in day   # numbers only


def test_without_prices_the_cost_cap_is_off(monkeypatch):
    _fresh(monkeypatch, PRICES=None, COST_DAY=0)
    with TestClient(host.app) as c:
        assert _run(c, "n1").status_code != 429


def test_the_landing_form_is_registered_and_read_only():
    with TestClient(host.app) as c:
        r = c.get("/agent/layouts/landing_loan")
        assert r.status_code == 200 and r.json()["form_id"] == "landing_loan"
        h = r.json()["jsx_hash"]
        assert c.get(f"/agent/layouts/{h}").status_code == 200
        assert c.get("/agent/layouts/nope").status_code == 404
    assert host.guide.packs.get("landing_loan").source == "dir"
    assert host.guide.tools_for("landing_loan") == []   # no tool with side effects on the public demo


def test_old_demo_conversations_are_deleted(monkeypatch, tmp_path):
    import os

    from formguide.transcript import FileTranscriptStore
    monkeypatch.setattr(host.guide, "transcripts", FileTranscriptStore(tmp_path))
    host.guide.transcripts.append("old1", {"id": "e", "kind": "user", "text": "x"})
    host.guide.transcripts.append("new1", {"id": "e", "kind": "user", "text": "x"})
    day_ago = os.path.getmtime(tmp_path / "old1.jsonl") - 25 * 3600
    os.utime(tmp_path / "old1.jsonl", (day_ago, day_ago))
    import asyncio
    assert asyncio.run(host.clean_up(24)) == 1
    assert not (tmp_path / "old1.jsonl").exists() and (tmp_path / "new1.jsonl").exists()
