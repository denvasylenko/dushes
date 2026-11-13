"""Server-side dictation: POST /transcribe on the form router and the site router."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from formguide.server import create_router
from formguide.transcribe import Transcriber, TranscriptionConfig

HEARD: list = []


def fake_whisper(data: bytes, filename: str, language: str | None) -> str:   # a host's own provider
    HEARD.append((len(data), filename, language))
    return " hello there "


def client(guide, prefix="/agent"):
    app = FastAPI()
    app.include_router(create_router(guide), prefix=prefix)
    return TestClient(app)


def test_config_parsing():
    assert TranscriptionConfig.parse(None) is None and TranscriptionConfig.parse(False) is None
    assert TranscriptionConfig.parse(True).provider == "faster_whisper"
    c = TranscriptionConfig.parse({"model": "base", "max_seconds": 30})
    assert (c.provider, c.model, c.max_seconds) == ("faster_whisper", "base", 30)
    with pytest.raises(ValueError, match="unknown"):
        TranscriptionConfig.parse({"modle": "base"})


def test_transcribe_endpoint(guide):
    HEARD.clear()
    guide.transcriber = Transcriber(TranscriptionConfig(provider="tests.test_transcribe:fake_whisper", max_bytes=1000))
    c = client(guide)
    r = c.post("/agent/transcribe", files={"file": ("rec.webm", b"\x1aE\xdf\xa3 audio", "audio/webm")}, data={"language": "ru-RU"})
    assert r.status_code == 200 and r.json() == {"text": "hello there", "language": "ru"}
    assert HEARD == [(10, "rec.webm", "ru")]
    big = c.post("/agent/transcribe", files={"file": ("rec.webm", b"x" * 2000, "audio/webm")})
    assert big.status_code == 413


def test_off_and_failing(guide):
    guide.transcriber = None
    c = client(guide)
    assert c.post("/agent/transcribe", files={"file": ("a.webm", b"x", "audio/webm")}).status_code == 501
    guide.transcriber = Transcriber(TranscriptionConfig(provider="tests.test_transcribe:nope"))
    assert c.post("/agent/transcribe", files={"file": ("a.webm", b"x", "audio/webm")}).status_code == 502


def test_the_site_router_transcribes_too(guide):
    from pathlib import Path

    from formguide.site import Dushes, SiteMap, create_dushes_router
    guide.transcriber = Transcriber(TranscriptionConfig(provider="tests.test_transcribe:fake_whisper"))
    site = Dushes(guide, SiteMap.load(Path(__file__).resolve().parents[1] / "demo" / "site.yaml"))
    app = FastAPI()
    app.include_router(create_dushes_router(site), prefix="/site")
    r = TestClient(app).post("/site/transcribe", files={"file": ("rec.webm", b"audio", "audio/webm")})
    assert r.json()["text"] == "hello there"
