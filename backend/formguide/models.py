"""Model configuration. Any LangChain chat model works: ChatAnthropic, ChatOpenAI,
AzureChatOpenAI, ChatGoogleGenerativeAI, a local model, or your own BaseChatModel.

A model can be given as
- an instance:  AzureChatOpenAI(azure_deployment="gpt-5", api_version=...)
- a string:     "anthropic:claude-haiku-5-5", "openai:gpt-5", "azure_openai:my-deployment"
- a dict:       {"provider": "anthropic", "model": "claude-haiku-5-5", "max_tokens": 16000}
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
        "agent": {"provider": "anthropic", "model": "claude-haiku-5-5", "max_tokens": 16000},
        "research": {"provider": "anthropic", "model": "claude-haiku-5-5", "max_tokens": 8000},
        "compile": {"provider": "anthropic", "model": "claude-haiku-5-5", "max_tokens": 16000},
        "extract": {"provider": "anthropic", "model": "claude-haiku-5-5", "max_tokens": 8000},
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

# a provider's key field on the LangChain model -> the environment variable that fills it
_KEY_FIELDS = {"anthropic_api_key": "ANTHROPIC_API_KEY", "openai_api_key": "OPENAI_API_KEY",
               "google_api_key": "GOOGLE_API_KEY", "mistral_api_key": "MISTRAL_API_KEY", "groq_api_key": "GROQ_API_KEY"}


def missing_key(model: Any) -> str | None:
    """The environment variable a model needs but has no key from, or None (a key is set, or the model
    authenticates another way: Azure AD, Bedrock, a local model, a scripted test model).
    Without it the provider's SDK fails with a vague "Connection error"."""
    if "azure" in type(model).__name__.lower():
        return None
    fields = getattr(type(model), "model_fields", {}) or {}
    for name, env in _KEY_FIELDS.items():
        if name not in fields:
            continue
        v = getattr(model, name, None)
        secret = v.get_secret_value() if hasattr(v, "get_secret_value") else v
        return None if secret else env
    return None


def missing_keys(models: dict[str, Any]) -> dict[str, str]:
    """{role: environment variable} for the roles whose model has no API key."""
    return {role: env for role, m in models.items() if m is not None and (env := missing_key(m))}


def provider_of(model: BaseChatModel) -> str:
    name = type(model).__name__.lower()
    for p in ("anthropic", "azure", "openai", "google", "bedrock", "ollama"):
        if p in name:
            return p
    return name


def system_message(text: str, model: BaseChatModel, cache: bool = True) -> SystemMessage:
    """Anthropic: mark the (stable) system prompt cacheable. Others: plain text (OpenAI, Azure OpenAI and
    Gemini cache a stable prefix by themselves)."""
    if cache and provider_of(model) == "anthropic":
        return SystemMessage(content=[{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}])
    return SystemMessage(content=text)


def cache_history(messages: list, model: BaseChatModel, cache: bool = True) -> list:
    """Anthropic: a cache breakpoint on the latest user message too, so every earlier turn is read from the
    cache (the history is append-only, so the prefix never changes). The messages are copied, never edited.
    Other providers: unchanged; their caching needs only the stable prefix the history already is."""
    if not cache or provider_of(model) != "anthropic":
        return messages
    from langchain_core.messages import HumanMessage

    i = next((k for k in range(len(messages) - 1, -1, -1) if isinstance(messages[k], HumanMessage)), None)
    if i is None:
        return messages
    m = messages[i]
    blocks = [{"type": "text", "text": m.content}] if isinstance(m.content, str) else [dict(b) if isinstance(b, dict) else b for b in m.content]
    last = next((k for k in range(len(blocks) - 1, -1, -1) if isinstance(blocks[k], dict) and blocks[k].get("type") == "text"), None)
    if last is None:
        return messages
    blocks[last] = {**blocks[last], "cache_control": {"type": "ephemeral"}}
    return [*messages[:i], m.model_copy(update={"content": blocks}), *messages[i + 1:]]


# Model APIs cap one image (Anthropic: 10 MB as base64, i.e. about 7.5 MB of bytes) and gain nothing from
# more than about 2000 px: phone photos are shrunk before they are sent.
IMAGE_MAX_BYTES = 3_500_000
IMAGE_MAX_SIDE = 2000


def fit_image(data: bytes, media_type: str) -> tuple[bytes, str]:
    """A photo small enough for the model: at most IMAGE_MAX_SIDE px and IMAGE_MAX_BYTES, as JPEG
    (PNG when it has transparency). Small images are returned unchanged."""
    try:
        from PIL import Image, ImageOps
    except ImportError:   # without Pillow only a clear error is possible
        if len(data) > IMAGE_MAX_BYTES * 2:
            raise ValueError("the image is too large for the model; install pillow to shrink photos") from None
        return data, media_type
    import io

    with Image.open(io.BytesIO(data)) as im:
        if len(data) <= IMAGE_MAX_BYTES and max(im.size) <= IMAGE_MAX_SIDE:
            return data, media_type
        im = ImageOps.exif_transpose(im)
        im.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
        alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        out = io.BytesIO()
        if alpha:
            im.save(out, "PNG", optimize=True)
            return out.getvalue(), "image/png"
        quality = 85
        while True:
            out = io.BytesIO()
            im.convert("RGB").save(out, "JPEG", quality=quality, optimize=True)
            if out.tell() <= IMAGE_MAX_BYTES or quality <= 45:
                return out.getvalue(), "image/jpeg"
            quality -= 15


def file_block(filename: str, media_type: str, data: bytes) -> dict[str, Any]:
    """A user file as a LangChain standard content block (converted per provider)."""
    if media_type.startswith("text/"):
        return {"type": "text", "text": f"<document name=\"{filename}\">\n"
                                        f"{data.decode('utf-8', errors='replace')}\n</document>"}
    if media_type.startswith("image/"):
        data, media_type = fit_image(data, media_type)
    b64 = base64.standard_b64encode(data).decode()
    if media_type.startswith("image/"):
        return {"type": "image", "base64": b64, "mime_type": media_type}
    return {"type": "file", "base64": b64, "mime_type": media_type, "filename": filename}


def structured(model: BaseChatModel, schema: type) -> Any:
    """Structured output via the provider's native JSON-schema mode.

    Not via forced tool calling: some models (e.g. Claude Haiku 5.5) reject a forced tool_choice.
    """
    try:
        return model.with_structured_output(schema, method="json_schema")
    except (TypeError, ValueError, NotImplementedError):
        return model.with_structured_output(schema)
