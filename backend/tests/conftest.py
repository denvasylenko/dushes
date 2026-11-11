"""Shared fixtures. No test calls a real model: ScriptedChatModel plays a script."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from formguide import FormGuide, GuideConfig, KnowledgeBase, Models, SkillRegistry
from formguide.domain.packs import DomainPackRegistry

DEMO = Path(__file__).resolve().parents[1] / "demo"
SAMPLES = DEMO / "samples"


class ScriptedChatModel(BaseChatModel):
    """Returns the next AIMessage of the script on every call; records what it was sent."""
    script: list[AIMessage] = Field(default_factory=list)
    calls: list[list[Any]] = Field(default_factory=list)
    bound: list[Any] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):  # type: ignore[override]
        self.bound = list(tools)
        return self

    def _next(self, messages) -> AIMessage:
        self.calls.append(list(messages))
        return self.script.pop(0) if self.script else AIMessage(content="(end of script)")

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next(messages))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self._next(messages)
        if msg.content:
            yield ChatGenerationChunk(message=AIMessageChunk(content=msg.content))
        for i, tc in enumerate(msg.tool_calls):
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[
                {"name": tc["name"], "args": json.dumps(tc["args"], ensure_ascii=False), "id": tc["id"], "index": i}]))


def say(text: str = "", *calls: tuple[str, str, dict]) -> AIMessage:
    return AIMessage(content=text, tool_calls=[{"name": n, "args": a, "id": i} for i, n, a in calls])


@pytest.fixture
def model() -> ScriptedChatModel:
    return ScriptedChatModel()


@pytest.fixture
def guide(tmp_path, model) -> FormGuide:
    return FormGuide(GuideConfig(
        models=Models(agent=model),
        data_dir=tmp_path,
        domain_packs=DomainPackRegistry(directory=DEMO / "domain_packs"),
        knowledge=KnowledgeBase(tmp_path / "kb", scopes={"loan_application": ["loan_application", "bank_common"]}),
        skills=SkillRegistry.from_dir(DEMO / "skills"),
    ))
