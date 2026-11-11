"""Long conversations: compaction of the chat history into a "conversation memory".

What grows in a long chat: a <form_context> block per turn (~1K tokens, and stale
after the next turn), tool results, and the dialogue itself. The form state never
needs summarizing: it is rebuilt from the config on every turn. So only the
dialogue is compacted:

- trigger: the history is above `max_history_tokens`;
- the last `keep_turns` user turns stay verbatim (their reasoning blocks are
  dropped: they were bound to the old prefix);
- everything older becomes a memory written by a (cheap) model: the user's goal,
  values the user gave that are not in the form yet (e.g. for a locked step),
  decisions and preferences, rejected proposals, open questions;
- the memory is merged with the previous one, so it survives many compactions,
  and is prepended to the first kept user message (no edits to the system prompt).

Provider-neutral: works with any chat model. A provider's native compaction can be
used instead by setting max_history_tokens=None and configuring it on the model.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from ..models import ModelSpec

TURN_ID = "formguide-turn:"   # id prefix of the HumanMessage that starts a user turn


@dataclass
class MemoryConfig:
    max_history_tokens: int | None = 60_000   # None disables compaction
    keep_turns: int = 4                       # recent user turns kept verbatim
    model: ModelSpec | None = None            # summarizer; default: the research model


SYSTEM = """You maintain the memory of a conversation between a user and an assistant that helps fill in a form ("{title}").
Write the updated memory in English using exactly these sections (omit empty ones):
## Goal
## Facts the user gave
One line each: what, the exact value, the field name if known, and status: in form / NOT YET IN FORM (and why: step locked, field hidden, user did not confirm).
## Decisions and preferences
## Rejected or declined
## Open questions / next step
Rules: keep exact values (names, numbers, dates, codes) as the user wrote them. Values not yet in the form are the most important: never drop them. Do not describe the form's current state (it is provided separately every turn). Be concise; merge with the previous memory and remove what is no longer true."""


def new_turn_id() -> str:
    return TURN_ID + uuid.uuid4().hex[:12]


def is_turn_start(m: BaseMessage) -> bool:
    return isinstance(m, HumanMessage) and str(m.id or "").startswith(TURN_ID)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def estimate_tokens(messages: list[BaseMessage]) -> int:
    n = 0
    for m in messages:
        n += len(_text(m.content))
        for c in getattr(m, "tool_calls", None) or []:
            n += len(json.dumps(c.get("args"), ensure_ascii=False))
    return round(n / 3.2)


def transcript(messages: list[BaseMessage]) -> str:
    """Old messages as plain text, without the bulky (and stale) form context blocks."""
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            parts = [b for b in (m.content if isinstance(m.content, list) else [{"type": "text", "text": m.content}])
                     if isinstance(b, dict) and b.get("type") == "text"]
            texts = [b["text"] for b in parts if not b["text"].startswith(("<form_context>", "<updated_instructions>",
                                                                          "<conversation_memory>"))]
            if texts:
                lines.append("USER: " + " ".join(t.strip() for t in texts))
        elif isinstance(m, AIMessage):
            if _text(m.content).strip():
                lines.append("ASSISTANT: " + _text(m.content).strip())
            for c in m.tool_calls:
                lines.append(f"ASSISTANT called {c['name']}({json.dumps(c.get('args'), ensure_ascii=False)[:300]})")
        elif isinstance(m, ToolMessage):
            lines.append(f"TOOL RESULT: {_text(m.content)[:300]}")
    return "\n".join(lines)


async def compact(messages: list[BaseMessage], memory: str, model: BaseChatModel, cfg: MemoryConfig,
                  title: str) -> tuple[list[BaseMessage], str] | None:
    """Returns (new history, new memory), or None if no compaction is needed."""
    if not cfg.max_history_tokens or estimate_tokens(messages) <= cfg.max_history_tokens:
        return None
    starts = [i for i, m in enumerate(messages) if is_turn_start(m)]
    if len(starts) <= cfg.keep_turns:
        return None
    cut = starts[-cfg.keep_turns] if cfg.keep_turns else len(messages) - 1
    old, kept = messages[:cut], messages[cut:]
    prompt = (f"<previous_memory>\n{memory or '(none)'}\n</previous_memory>\n"
              f"<conversation_to_add>\n{transcript(old)}\n</conversation_to_add>\nWrite the updated memory.")
    reply = await model.ainvoke([SystemMessage(content=SYSTEM.format(title=title)), HumanMessage(content=prompt)])
    new_memory = _text(reply.content).strip() or memory

    from .graph import strip_reasoning   # local import: graph imports this module

    kept = strip_reasoning(kept)
    first = kept[0]
    blocks = first.content if isinstance(first.content, list) else [{"type": "text", "text": first.content}]
    note = {"type": "text", "text": "<conversation_memory>\nEarlier parts of this conversation, summarized:\n"
                                    f"{new_memory}\n</conversation_memory>"}
    kept[0] = first.model_copy(update={"content": [note, *blocks]})
    return kept, new_memory
