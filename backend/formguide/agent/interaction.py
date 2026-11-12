"""How a resume answers the waiting card or question.

Shared by the graph (what the model is told) and the transcript (what the user saw),
so both always agree. A resume value is a dict built by agui.run_kwargs or passed to
FormGuide.run(resume=...).
"""
from __future__ import annotations

import re
from datetime import date, datetime
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
    inp = question.get("input")
    if text and inp and not ids:
        why = input_problem(inp, text)
        if why:
            return None, why
    if not ids and not text:
        return None, ""
    out: dict[str, Any] = {}
    if ids:
        out["ids"] = ids
        out["labels"] = [by_id[i] for i in ids]
    if text:
        out["text"] = text
    return out, ""


def read_field_answers(question: dict, resume: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """A several-fields question -> ({name: value} the user gave, problems)."""
    got = resume.get("answers") if isinstance(resume.get("answers"), dict) else {}
    out: dict[str, str] = {}
    problems: list[str] = []
    for f in question.get("fields") or []:
        v = str(got.get(f["name"]) or "").strip()
        if not v:
            if f.get("required"):
                problems.append(f"{f['label']} was left empty")
            continue
        why = input_problem(f["input"], v) if f.get("input") else ""
        if why:
            problems.append(f"{f['label']}: {why}")
            continue
        out[f["name"]] = v
    return out, problems


def read_review(resume: dict[str, Any]) -> tuple[str, dict]:
    """A review card -> (action: continue | submit | fixed | closed, details)."""
    action = resume.get("action") if isinstance(resume, dict) else None
    if action == "fixed" and isinstance(resume.get("names"), list) and resume.get("config"):
        return "fixed", {"names": [str(n) for n in resume["names"]]}
    if action == "submit":
        return "submit", {}
    if action == "continue":
        return "continue", {"section": str(resume.get("section") or "")}
    return "closed", {}


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


# ---------------------------------------------------------------- typed answers (ask_user input)


def _parse(kind: str, value: Any) -> Any:
    s = str(value).strip()
    if kind == "number":
        return float(s.replace(" ", "").replace(",", "."))
    if kind == "date":
        return date.fromisoformat(s)
    if kind == "datetime":
        return datetime.fromisoformat(s)
    if kind == "time":
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", s):
            raise ValueError("not HH:MM")
        return s
    return s


def input_ok(kind: str, value: Any) -> bool:
    try:
        _parse(kind, value)
        return True
    except (ValueError, TypeError):
        return False


def input_problem(inp: dict, text: str) -> str:
    """Why a typed answer does not fit the question's input, or ''."""
    kind = inp.get("type") or "text"
    try:
        v = _parse(kind, text)
    except (ValueError, TypeError):
        fmt = {"date": "YYYY-MM-DD", "time": "HH:MM", "datetime": "YYYY-MM-DDTHH:MM", "number": "a number"}.get(kind)
        return f"the answer {text!r} is not {fmt}" if fmt else ""
    for k, cmp in (("min", lambda a, b: a < b), ("max", lambda a, b: a > b)):
        if inp.get(k) not in (None, ""):
            try:
                if cmp(v, _parse(kind, inp[k])):
                    return f"the answer {text!r} is out of range ({k} {inp[k]})"
            except (ValueError, TypeError):
                pass
    return ""


# ---------------------------------------------------------------- edits, uploads, confirmations


def read_edits(changes: list[dict], resume: dict[str, Any], applied: list[str]) -> dict[str, Any]:
    """Values the user changed on the card before applying (only for applied rows)."""
    edited = resume.get("edited") if isinstance(resume.get("edited"), dict) else {}
    proposed = {c["name"]: c.get("value") for c in changes}
    return {k: v for k, v in edited.items() if k in applied and v != proposed.get(k)}


def read_upload(resume: dict[str, Any], lookup) -> list[dict]:
    """An upload request -> [{id, filename}] of the uploaded files that exist in this thread."""
    ids = resume.get("attachment_ids") if isinstance(resume.get("attachment_ids"), list) else []
    out = []
    for i in ids:
        found = lookup(str(i))
        if found and not any(o["id"] == str(i) for o in out):
            out.append({"id": str(i), "filename": found})
    return out


def upload_text(files: list[dict]) -> str:
    if not files:
        return "The user did not upload a file (skipped the request)."
    return ("The user uploaded: " + ", ".join(f"{f['filename']} (attachment_id={f['id']})" for f in files)
            + ". Read it with extract_from_attachment.")


def read_confirm(resume: dict[str, Any]) -> bool:
    if "accepted" in resume:
        return bool(resume.get("accepted"))
    text = str((resume.get("answer") or {}).get("text") or "") if isinstance(resume.get("answer"), dict) else ""
    return text.strip().lower() in _YES
