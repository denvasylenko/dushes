"""The public host (docs_ai.host): the docs assistant mounted next to the demo, and the demo's limits."""
from __future__ import annotations

from fastapi.testclient import TestClient

from docs_ai import host


def _run(c, thread="t1", resume=False):
    body = {"threadId": thread, "runId": "r", "state": {}, "messages": [{"id": "m", "role": "user", "content": "hi"}],
            "tools": [], "context": [], "forwardedProps": {"command": {"resume": {"accepted": False}}} if resume else {}}
    return c.post("/agent/run", json=body)


def test_document_uploads_are_off():
    with TestClient(host.app) as c:
        assert c.post("/agent/kb/loan_application/documents").status_code == 403
        assert c.delete("/agent/kb/loan_application/documents/x").status_code == 403


def test_a_demo_chat_has_a_limit_and_card_answers_do_not_count(monkeypatch):
    monkeypatch.setattr(host, "PER_THREAD", 2)
    host._threads.clear()
    with TestClient(host.app) as c:
        codes = [_run(c, "lim").status_code for _ in range(2)]
        assert 429 not in codes
        assert _run(c, "lim", resume=True).status_code != 429   # answering a card is not a new message
        r = _run(c, "lim")
        assert r.status_code == 429 and "2 messages" in r.json()["detail"]


def test_the_docs_assistant_is_mounted():
    with TestClient(host.app) as c:
        assert c.get("/ai/health").status_code == 200
