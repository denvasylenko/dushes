"""Prompt caching: a breakpoint on the history for Anthropic, nothing for providers that cache by themselves."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from formguide.config import load_config
from formguide.models import cache_history, system_message


class ChatAnthropicFake:   # provider_of() reads the class name
    pass


class ChatOpenAIFake:
    pass


def test_the_latest_user_message_gets_the_breakpoint():
    hist = [HumanMessage("hi"), AIMessage("hello"),
            HumanMessage(content=[{"type": "text", "text": "<form_context>..."}, {"type": "text", "text": "a car loan"}]),
            AIMessage(content="", tool_calls=[{"id": "t1", "name": "get_fields", "args": {}}]),
            ToolMessage("fields", tool_call_id="t1")]
    out = cache_history(hist, ChatAnthropicFake())
    assert out[2].content[-1]["cache_control"] == {"type": "ephemeral"}          # the last text block of the turn
    assert "cache_control" not in out[2].content[0] and out[4] is hist[4]
    assert "cache_control" not in hist[2].content[-1]                             # the state is never edited
    assert cache_history(hist, ChatOpenAIFake()) is hist                          # OpenAI caches a stable prefix itself
    assert cache_history(hist, ChatAnthropicFake(), cache=False) is hist


def test_the_system_prompt_and_the_switch(tmp_path):
    assert system_message("rules", ChatAnthropicFake()).content[0]["cache_control"]
    assert system_message("rules", ChatAnthropicFake(), cache=False).content == "rules"
    assert system_message("rules", ChatOpenAIFake()).content == "rules"
    p = tmp_path / "formguide.yaml"
    p.write_text("model: anthropic:claude-haiku-5-5\nprompt_cache: off\n")
    assert load_config(p).prompt_cache == "off"
    p.write_text("model: anthropic:claude-haiku-5-5\n")
    assert load_config(p).prompt_cache == "auto"


def test_warm_up_loads_the_model_in_the_background(monkeypatch):
    import threading

    from formguide.transcribe import Transcriber, TranscriptionConfig
    done = threading.Event()
    t = Transcriber(TranscriptionConfig())
    monkeypatch.setattr(t, "_load", lambda: done.set())
    t.warm_up()
    assert done.wait(2)
    other = Transcriber(TranscriptionConfig(warm=False))
    monkeypatch.setattr(other, "_load", lambda: (_ for _ in ()).throw(AssertionError("no warm-up")))
    other.warm_up()
