"""Chat-side safety defaults of the HTTP router: no debug view by default, bounded inputs."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from formguide import server
from formguide.server import create_router


def client(guide, **kw) -> TestClient:
    app = FastAPI()
    app.include_router(create_router(guide, **kw), prefix="/agent")
    return TestClient(app)


def test_debug_view_is_off_by_default(guide):
    assert client(guide).get("/agent/debug/t1").status_code == 404


def test_oversized_layout_is_refused(guide, monkeypatch):
    monkeypatch.setattr(server, "MAX_JSX_CHARS", 100)
    r = client(guide).post("/agent/layouts", json={"jsx": "<Form>" + "x" * 200 + "</Form>"})
    assert r.status_code == 413


def test_oversized_attachment_is_refused(guide, monkeypatch):
    monkeypatch.setattr(guide.attachments, "max_bytes", 1024)
    c = client(guide)
    r = c.post("/agent/attachments", data={"thread_id": "t1"}, files={"file": ("big.txt", b"a" * 5000, "text/plain")})
    assert r.status_code == 400 and "larger than" in r.json()["detail"]
    ok = c.post("/agent/attachments", data={"thread_id": "t1"}, files={"file": ("small.txt", b"a" * 1024, "text/plain")})
    assert ok.status_code == 200 and ok.json()["bytes"] == 1024
