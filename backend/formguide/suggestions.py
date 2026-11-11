"""Quick replies: a few short next messages the user may want to send after an answer.

A separate call to a cheap model (config `suggestions`), made after the turn and outside the
graph, so it never enters the model's history. Failures and timeouts are silent.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

log = logging.getLogger(__name__)

SYSTEM = """You suggest what the user of a form assistant might want to send next.
Reply with JSON only: {"items": ["...", "..."]}.
Rules: at most {max} items; each is a short message from the user's point of view (2 to 7 words);
in the language the user writes in; concrete next steps for this form, not generic chit-chat;
never repeat what was just answered; no field values the user did not give."""


def _parse(text: str, limit: int) -> list[str]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0)).get("items") or []
    except (ValueError, AttributeError):
        return []
    out: list[str] = []
    for x in items:
        s = " ".join(str(x).split())[:80]
        if s and s not in out:
            out.append(s)
    return out[:limit]


async def suggest(model: Any, *, user_text: str, answer: str, context: str, limit: int, timeout: float) -> list[str]:
    msgs = [SystemMessage(content=SYSTEM.replace("{max}", str(limit))),
            HumanMessage(content=f"<form>\n{context[:3000]}\n</form>\n<user>\n{user_text[:1000]}\n</user>\n"
                                 f"<assistant>\n{answer[:2000]}\n</assistant>")]
    try:
        res = await asyncio.wait_for(model.ainvoke(msgs), timeout)
    except Exception as e:  # noqa: BLE001 - suggestions are optional
        log.info("suggestions skipped: %s", type(e).__name__)
        return []
    content = res.content if isinstance(res.content, str) else " ".join(
        b.get("text", "") for b in res.content if isinstance(b, dict))
    return _parse(content, limit)
