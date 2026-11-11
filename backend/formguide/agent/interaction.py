"""How a resume answers the waiting card or question.

Shared by the graph (what the model is told) and the transcript (what the user saw),
so both always agree. A resume value is a dict built by agui.run_kwargs or passed to
FormGuide.run(resume=...).
"""
from __future__ import annotations

from typing import Any

_YES = {"yes", "y", "ok", "accept", "accepted", "true"}


def read_decision(changes: list[dict], resume: dict[str, Any]) -> tuple[list[str], list[str]]:
    """A field-change card -> (applied names, declined names). Nothing applied means rejected."""
    names = [c["name"] for c in changes]
    accepted = bool(resume.get("accepted"))
    if not accepted and "answer" in resume:   # a typed "yes" / "ok" from a client that only sends text
        accepted = str((resume.get("answer") or {}).get("text") or "").strip().lower() in _YES
    if not accepted:
        return [], names
    keep = resume.get("names")
    if keep is None:
        return names, []
    keep = {str(k) for k in keep} if isinstance(keep, list) else set()
    return [n for n in names if n in keep], [n for n in names if n not in keep]


def read_answer(question: dict, resume: dict[str, Any]) -> tuple[dict | None, str]:
    """A question card -> (answer {ids?, labels?, text?} or None if skipped, why it was skipped)."""
    if resume.get("accepted") is False and "answer" not in resume:
        return None, ""
    ans = resume.get("answer")
    if isinstance(ans, str):
        ans = {"text": ans}
    if not isinstance(ans, dict):
        return None, ""
    by_id = {o["id"]: o["label"] for o in question.get("options") or []}
    ids = [str(i) for i in ans.get("ids") or []] if isinstance(ans.get("ids"), list) else []
    text = str(ans.get("text") or "").strip()
    bad = [i for i in ids if i not in by_id]
    if bad:
        return None, f"the answer {', '.join(bad)} was not one of the options"
    if len(ids) > 1 and not question.get("multiple"):
        return None, "several options were sent for a single-choice question"
    if text and not question.get("allow_text"):
        return None, "a typed answer was sent but the question allowed only the options"
    if not ids and not text:
        return None, ""
    out: dict[str, Any] = {}
    if ids:
        out["ids"] = ids
        out["labels"] = [by_id[i] for i in ids]
    if text:
        out["text"] = text
    return out, ""


def answer_text(answer: dict | None, why: str = "") -> str:
    """The tool result the model gets for a question."""
    if answer is None:
        return "The user skipped the question." + (f" ({why})" if why else "")
    parts = []
    if answer.get("ids"):
        parts.append("The user chose: " + ", ".join(f"{lbl} ({i})" for lbl, i in zip(answer["labels"], answer["ids"])))
    if answer.get("text"):
        parts.append(f"The user wrote: {answer['text']}")
    return ". ".join(parts)
