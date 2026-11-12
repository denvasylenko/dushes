"""The docs assistant (docs_ai): corpus splitting, retrieval, the AG-UI stream and the abuse limits."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from docs_ai.app import Limiter, create_app
from docs_ai.corpus import load, slug, split

from .conftest import ScriptedChatModel

CORPUS = """<!-- page: https://docs.example/backend/models/ -->
# Models and providers

> Four roles, any LangChain chat model for each.

## Pick a provider

Azure OpenAI for the agent:

```yaml
models:
  agent: {class: "langchain_openai:AzureChatOpenAI", azure_deployment: gpt-5}
  research: "openai:gpt-5-mini"
```

---

<!-- page: https://docs.example/frontend/themes/ -->
# Themes and styling

> Named themes, tokens on the element and ::part().

## Tokens on the element

Set --agui-accent on the element to change the accent colour of the chat widget.
"""


def _events(body: str) -> list[dict]:
    return [json.loads(line[5:]) for line in body.splitlines() if line.startswith("data:")]


def _client(tmp_path, script=None, **kw):
    path = tmp_path / "llms-full.txt"
    path.write_text(CORPUS)
    model = ScriptedChatModel(script=[AIMessage(content="Use `models:`.\n\nSources: [Pick a provider](https://docs.example/backend/models/#pick-a-provider)")])
    if script:
        model.script = script   # may hold exceptions (a provider error)
    app = create_app(corpus_source=str(path), model=model, origins=["https://docs.example"], refresh=0, **kw)
    return TestClient(app), model


def _ask(c, text, ip=None):
    body = {"threadId": "t1", "runId": "r1", "state": {}, "messages": [{"id": "m1", "role": "user", "content": text}],
            "tools": [], "context": [], "forwardedProps": {}}
    return c.post("/ask/run", json=body, headers={"Accept": "text/event-stream"})


def test_split_into_sections_with_anchors():
    chunks = split(CORPUS)
    ids = {c.doc_id for c in chunks}
    assert "https://docs.example/backend/models/#pick-a-provider" in ids
    assert "https://docs.example/frontend/themes/#tokens-on-the-element" in ids
    assert slug("Send the form with `every` message") == "send-the-form-with-every-message"


def test_retrieval_finds_the_right_page(tmp_path):
    p = tmp_path / "c.txt"
    p.write_text(CORPUS)
    c = load(str(p))
    assert c.pages == 2
    assert c.search("azure openai research model")[0].doc_id.endswith("/backend/models/#pick-a-provider")
    assert c.search("accent colour of the widget")[0].doc_id.endswith("#tokens-on-the-element")


def test_stream_has_search_step_answer_and_end(tmp_path):
    with _client(tmp_path)[0] as c:
        r = _ask(c, "How do I use Azure OpenAI for the agent?")
        assert r.status_code == 200
        types = [e["type"] for e in _events(r.text)]
        assert types[0] == "RUN_STARTED" and types[-1] == "RUN_FINISHED"
        assert "TOOL_CALL_START" in types and "TEXT_MESSAGE_CONTENT" in types


def test_passages_reach_the_model(tmp_path):
    client, model = _client(tmp_path)
    with client as c:
        _ask(c, "azure openai agent")
    system = model.calls[0][0].content
    assert "AzureChatOpenAI" in system and "https://docs.example/backend/models/#pick-a-provider" in system


def test_limits(tmp_path):
    with _client(tmp_path, per_minute=1, max_chars=50)[0] as c:
        assert _ask(c, "x" * 51).status_code == 413
        assert _ask(c, "themes").status_code == 200
        assert _ask(c, "themes again").status_code == 429


def test_cors_only_for_the_site(tmp_path):
    with _client(tmp_path)[0] as c:
        ok = c.options("/ask/run", headers={"Origin": "https://docs.example", "Access-Control-Request-Method": "POST"})
        bad = c.options("/ask/run", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
        assert ok.headers.get("access-control-allow-origin") == "https://docs.example"
        assert "access-control-allow-origin" not in bad.headers


def test_model_error_is_a_human_run_error(tmp_path):
    with _client(tmp_path, script=[RuntimeError("boom")])[0] as c:
        evs = _events(_ask(c, "themes").text)
        assert evs[-1]["type"] == "RUN_ERROR" and "boom" not in evs[-1]["message"]


def test_limiter_day_window():
    lim = Limiter(per_minute=100, per_day=2)
    assert lim.allow("a", 0) and lim.allow("a", 100)
    assert not lim.allow("a", 200)
    assert lim.allow("a", 86500)


def test_guides_rank_above_specs_and_diagrams_are_dropped():
    text = CORPUS + """
---

<!-- page: https://docs.example/specifications/chat-widget/ -->
# chat-widget

## Accent colour tokens
The widget SHALL read the accent colour token --agui-accent of the chat widget.

```mermaid
flowchart LR
  accent --> widget
```
"""
    chunks = split(text)
    assert not any("flowchart" in c.text for c in chunks)
    from formguide import BM25Index
    from docs_ai.corpus import Corpus
    idx = BM25Index()
    idx.add(chunks)
    top = Corpus(idx, 3, len(chunks), "x").search("accent colour of the chat widget", k=2)
    assert top[0].doc_id.endswith("/frontend/themes/#tokens-on-the-element")
