"""Replies to quotes: the user picked parts of the agent's messages and answers them, as in the Claude app.

The client sends `forwardedProps.reply_to` as a list, in the order the user collected them:
`[{message_id, quote, note?} | {message_id, whole: true, note?}]` (an old client: one such object). The
transcript keeps the list on the user's entry (a reload draws every quote and note above the bubble), and the
agent reads one line per quote before the message.
"""
from __future__ import annotations

import re
from typing import Any

QUOTE_MAX = 300
NOTE_MAX = 1000
MAX_QUOTES = 10


def _one(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    mid = str(raw.get("message_id") or "").strip()[:100]
    note = re.sub(r"\s+", " ", str(raw.get("note") or "")).strip()[:NOTE_MAX]
    extra = {**({"message_id": mid} if mid else {}), **({"note": note} if note else {})}
    if raw.get("whole") is True:   # a reply to the whole answer: the server finds its text by message_id
        return {"whole": True, **extra}
    quote = re.sub(r"\s+", " ", str(raw.get("quote") or "")).strip()
    if not quote:
        return None
    if len(quote) > QUOTE_MAX:
        quote = quote[:QUOTE_MAX - 1].rstrip() + "\u2026"
    return {"quote": quote, **extra}


def clean(raw: Any) -> list[dict[str, Any]] | None:
    """The client's reply_to (a list, or one object from an old client) -> a clean list, or None."""
    items = raw if isinstance(raw, list) else [raw]
    out = [x for x in (_one(r) for r in items[:MAX_QUOTES]) if x]
    return out or None


def as_list(stored: Any) -> list[dict[str, Any]] | None:
    """A transcript's reply_to as a list (entries written before lists held one object)."""
    if not stored:
        return None
    return stored if isinstance(stored, list) else [stored]


def resolve(reply_to: list[dict[str, Any]] | None, entries: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """For each reply to a whole answer, the beginning of that answer (found by message_id in the transcript),
    as `text`; the stored list stays as the client sent it."""
    reply_to = as_list(reply_to)
    if not reply_to:
        return reply_to
    out = []
    for r in reply_to:
        if r.get("whole"):
            mid = r.get("message_id")
            e = next((x for x in reversed(entries)
                      if x["kind"] == "assistant" and mid and x.get("message_id") == mid), None)
            text = re.sub(r"\s+", " ", str((e or {}).get("text") or "")).strip()
            r = {**r, **({"text": text[:600]} if text else {})}
        out.append(r)
    return out


def quoted(message: str | None, reply_to: list[dict[str, Any]] | None) -> str | None:
    """The message as the agent reads it: every quote it answers, with the user's comment, then the text."""
    reply_to = as_list(reply_to)
    if not reply_to or message is None:
        return message
    lines = []
    for r in reply_to:
        if r.get("whole"):
            said = f": \u00ab{r['text']}\u00bb" if r.get("text") else " (your previous answer)"
            line = f"[The user replies to your whole earlier answer{said}]"
        else:
            line = f"[The user replies to this part of your earlier answer: \u00ab{r['quote']}\u00bb]"
        if r.get("note"):
            line += f" Their comment: \u00ab{r['note']}\u00bb"
        lines.append(line)
    return "\n".join(lines) + (f"\n{message}" if message else "")
