"""Model configuration. Any LangChain chat model works: ChatAnthropic, ChatOpenAI,
AzureChatOpenAI, ChatGoogleGenerativeAI, a local model, or your own BaseChatModel.

A model can be given as
- an instance:  AzureChatOpenAI(azure_deployment="gpt-5", api_version=...)
- a string:     "anthropic:claude-opus-5-5", "openai:gpt-5", "azure_openai:my-deployment"
- a dict:       {"provider": "anthropic", "model": "claude-opus-5-5", "max_tokens": 16000}
- a class dict: {"class": "langchain_openai:AzureChatOpenAI", "azure_deployment": "gpt-5", ...}
Strings and dicts go through langchain.chat_models.init_chat_model; the provider's
LangChain package must be installed (langchain-anthropic, langchain-openai, ...).

The model needs tool calling (agent, research) and structured output (compile,
extract); extraction also needs vision / PDF input for scans.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage

ModelSpec = BaseChatModel | str | dict[str, Any]


def build_model(spec: ModelSpec) -> BaseChatModel:
    if isinstance(spec, BaseChatModel):
        return spec
    from langchain.chat_models import init_chat_model

    if isinstance(spec, str):
        return init_chat_model(spec)
    d = dict(spec)
    if "class" in d:   # {"class": "langchain_openai:AzureChatOpenAI", ...constructor kwargs}
        from .skills import import_object

        return import_object(d.pop("class"))(**d)
    model = d.pop("model")
    provider = d.pop("provider", None)
    return init_chat_model(model, model_provider=provider, **d)


def anthropic_defaults() -> dict[str, ModelSpec]:
    """Defaults when nothing is configured (needs ANTHROPIC_API_KEY)."""
    return {
        "agent": {"provider": "anthropic", "model": "claude-opus-5-5", "max_tokens": 16000,
                  "output_config": {"effort": "low"}},
        "research": {"provider": "anthropic", "model": "claude-sonnet-5-5", "max_tokens": 8000},
        "compile": {"provider": "anthropic", "model": "claude-opus-5-5", "max_tokens": 16000,
                    "output_config": {"effort": "medium"}},
        "extract": {"provider": "anthropic", "model": "claude-opus-5-5", "max_tokens": 8000,
                    "output_config": {"effort": "low"}},
    }


@dataclass
class Models:
    """One model per role. Unset roles fall back to `agent`."""
    agent: ModelSpec
    research: ModelSpec | None = None   # document researcher: a cheaper model is fine
    compile: ModelSpec | None = None    # documents -> domain pack, offline
    extract: ModelSpec | None = None    # user attachments -> field values; needs vision

    @classmethod
    def anthropic(cls) -> "Models":
        return cls(**anthropic_defaults())

    def resolve(self) -> "ResolvedModels":
        agent = build_model(self.agent)
        return ResolvedModels(
            agent=agent,
            research=build_model(self.research) if self.research else agent,
            compile=build_model(self.compile) if self.compile else agent,
            extract=build_model(self.extract) if self.extract else agent,
        )


@dataclass
class ResolvedModels:
    agent: BaseChatModel
    research: BaseChatModel
    compile: BaseChatModel
    extract: BaseChatModel
    memory: BaseChatModel | None = None   # summarizer for long chats (set by FormGuide; default: research)


# ===================================================================== provider-specific touches


def provider_of(model: BaseChatModel) -> str:
    name = type(model).__name__.lower()
    for p in ("anthropic", "azure", "openai", "google", "bedrock", "ollama"):
        if p in name:
            return p
    return name


def system_message(text: str, model: BaseChatModel) -> SystemMessage:
    """Anthropic: mark the (stable) system prompt cacheable. Others: plain text."""
    if provider_of(model) == "anthropic":
        return SystemMessage(content=[{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}])
    return SystemMessage(content=text)


def file_block(filename: str, media_type: str, data: bytes) -> dict[str, Any]:
    """A user file as a LangChain standard content block (converted per provider)."""
    if media_type.startswith("text/"):
        return {"type": "text", "text": f"<document name=\"{filename}\">\n"
                                        f"{data.decode('utf-8', errors='replace')}\n</document>"}
    b64 = base64.standard_b64encode(data).decode()
    if media_type.startswith("image/"):
        return {"type": "image", "base64": b64, "mime_type": media_type}
    return {"type": "file", "base64": b64, "mime_type": media_type, "filename": filename}


def structured(model: BaseChatModel, schema: type) -> Any:
    """Structured output via the provider's native JSON-schema mode.

    Not via forced tool calling: some models (e.g. Claude Opus 5.5) reject a forced tool_choice.
    """
    try:
        return model.with_structured_output(schema, method="json_schema")
    except (TypeError, ValueError, NotImplementedError):
        return model.with_structured_output(schema)
