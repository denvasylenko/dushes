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


def test_table_of_contents_lists_guides_and_reaches_the_model(tmp_path):
    from docs_ai.corpus import contents

    toc = contents(CORPUS + "\n---\n\n<!-- page: https://docs.example/specifications/x/ -->\n# x\n\nbody\n")
    assert toc.splitlines() == [
        "- [Models and providers](https://docs.example/backend/models/): Four roles, any LangChain chat model for each.",
        "- [Themes and styling](https://docs.example/frontend/themes/): Named themes, tokens on the element and ::part().",
    ]
    client, model = _client(tmp_path)
    with client as c:
        _ask(c, "where are all the ways to set a model?")
    system = model.calls[0][0].content
    assert "Table of contents" in system and "](https://docs.example/frontend/themes/)" in system


def test_code_blocks_get_ids_and_markers():
    from docs_ai.corpus import mark_blocks

    chunks = split(CORPUS)
    blocks = mark_blocks(chunks)
    assert list(blocks) == ["b1"]
    b = blocks["b1"]
    assert b.lang == "yaml" and b.code.startswith("models:\n  agent:") and b.url.endswith("#pick-a-provider")
    assert any("[code b1 \u00b7 yaml \u00b7 yaml]" in c.text for c in chunks)


def test_answer_text_then_cards_then_follow_ups(tmp_path):
    from .conftest import say

    script = [say("Set the roles under `models:`.",
                  ("c1", "show_code", {"blocks": ["b1", "b999"]}),
                  ("c2", "show_pages", {"urls": ["https://docs.example/backend/models/#pick-a-provider"]}),
                  ("c3", "suggest_next", {"questions": ["How do I mix providers?", "Which roles are there?"]}))]
    client, model = _client(tmp_path, script=script)
    with client as c:
        evs = _events(_ask(c, "azure openai agent").text)
    kinds = [e["type"] if e["type"] != "CUSTOM" else e["name"] for e in evs]
    assert kinds.index("TEXT_MESSAGE_END") < kinds.index("docs_card") < kinds.index("suggestions") < kinds.index("RUN_FINISHED")
    cards = [e["value"] for e in evs if e.get("name") == "docs_card"]
    assert cards[0]["kind"] == "code" and [b["id"] for b in cards[0]["blocks"]] == ["b1"]   # b999 does not exist
    assert cards[0]["blocks"][0]["code"].startswith("models:\n  agent: {class:")              # verbatim from the docs
    assert len(cards) == 1   # the page card named the same page as the code's source line: not repeated
    assert [e["value"] for e in evs if e.get("name") == "suggestions"] == [{"items": ["How do I mix providers?", "Which roles are there?"]}]
    assert "[code b1" in model.calls[0][0].content   # the model sees the block ids


def test_a_conversation_has_a_limit(tmp_path):
    client, _ = _client(tmp_path, per_thread=2)
    with client as c:
        assert [_ask(c, "q").status_code for _ in range(3)] == [200, 200, 429]
        assert "limit" in _ask(c, "q").json()["detail"]


def test_page_cards_name_their_sidebar_group():
    from docs_ai.agent import _group

    assert _group("https://x.example/reference/configuration/") == "Reference"
    assert _group("https://x.example/dushes/agents/shared/configuration/") == "Agents"
    assert _group("https://x.example/dushes/agents/ui-agent/prefill/") == "UI agent"
    assert _group("https://x.example/reference/specifications/dushes/") == "Specifications"
    assert _group("https://x.example/") == ""


def test_a_long_code_block_is_never_cut():
    from docs_ai.corpus import _pieces

    code = "```yaml\n" + "\n\n".join(f"key{i}: value  # a comment long enough to fill the piece {'x' * 60}" for i in range(60)) + "\n```"
    pieces = _pieces("Intro.\n\n" + code + "\n\nAfter.", size=600)
    assert sum(p.count("```") for p in pieces) == 2 and any(p.count("```") == 2 for p in pieces)


def test_whole_config_questions_match():
    from docs_ai.agent import WHOLE_CONFIG

    for q in ["Show me the whole configuration with every key", "all config options", "full yaml please",
              "the complete config file"]:
        assert WHOLE_CONFIG.search(q), q
    assert not WHOLE_CONFIG.search("How do I use Azure OpenAI?")


def test_whole_config_card_puts_yaml_first():
    from docs_ai.agent import whole_config_card
    from docs_ai.corpus import Block, Corpus
    from formguide import BM25Index

    c = Corpus(BM25Index(), 1, 1, "x", blocks={
        "b1": Block("b1", "python", "app.py", "GuideConfig()", "u#every-key-in-one-file", "Configuration", "Every key in one file"),
        "b2": Block("b2", "yaml", "formguide.yaml", "model: x", "u#every-key-in-one-file", "Configuration", "Every key in one file")})
    card = whole_config_card(c)
    assert [b["lang"] for b in card["blocks"]] == ["yaml", "python"]
