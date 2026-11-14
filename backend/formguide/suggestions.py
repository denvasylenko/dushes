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
Reply with JSON only: {"items": ["...", {"text": "...", "set": {"<field name>": <value>}}]}.
Rules: at most {max} items; each is a short message from the user's point of view (2 to 7 words);
in the language the user writes in; concrete next steps for this form, not generic chit-chat;
never repeat what was just answered or what the form already has; no field values the user did not give.
An item MAY be an object with "set" when choosing it means filling fields: only with a value the user
or the assistant named in this exchange (e.g. the assistant offered a 48-month term), field names
exactly as in <form>, values as plain text, numbers or YYYY-MM-DD dates. Otherwise use a plain string."""


def _parse(text: str, limit: int) -> list[dict[str, Any]]:
    """The model's reply -> [{text, set?}], at most `limit`, without duplicates."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0)).get("items") or []
    except (ValueError, AttributeError):
        return []
    out: list[dict[str, Any]] = []
    for x in items:
        raw, sets = (x.get("text"), x.get("set")) if isinstance(x, dict) else (x, None)
        s = " ".join(str(raw or "").split())[:80]
        if s and all(o["text"] != s for o in out):
            out.append({"text": s, **({"set": sets} if isinstance(sets, dict) and sets else {})})
    return out[:limit]


async def suggest(model: Any, *, user_text: str, answer: str, context: str, limit: int,
                  timeout: float, meta: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Quick replies after an answer; `meta`, when given, gets the call's `usage` and `model` for run_stats."""
    msgs = [SystemMessage(content=SYSTEM.replace("{max}", str(limit))),
            HumanMessage(content=f"<form>\n{context[:3000]}\n</form>\n<user>\n{user_text[:1000]}\n</user>\n"
                                 f"<assistant>\n{answer[:2000]}\n</assistant>")]
    try:
        res = await asyncio.wait_for(model.ainvoke(msgs), timeout)
    except Exception as e:  # noqa: BLE001 - suggestions are optional
        log.info("suggestions skipped: %s", type(e).__name__)
        return []
    if meta is not None:
        rm = getattr(res, "response_metadata", None) or {}
        meta["usage"] = dict(getattr(res, "usage_metadata", None) or {}) or None
        meta["model"] = str(rm.get("model_name") or rm.get("model") or "") or None
    content = res.content if isinstance(res.content, str) else " ".join(
        b.get("text", "") for b in res.content if isinstance(b, dict))
    return _parse(content, limit)
