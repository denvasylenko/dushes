"""Ask AI (the docs assistant, backend/docs_ai) answers checked against the docs: each question runs N times and a
run is a hit when the answer (its text and its cards' code) says what it must and never what it must not.

    uv run python scripts/ask_ai_evals.py                  # every question in evals/ask_ai/, in-process
    uv run python scripts/ask_ai_evals.py azure_cheaper_research --runs 5

A question (evals/ask_ai/<name>.yaml): name, ask (or turns: [..] in one thread, the history sent back with its
toolCalls as the widget does; the checks read the last answer), runs (default 3), says: [[alternatives], ...],
never_says: [...], no_repeated_cards, first_turn_cards, highlights_first_card (the last answer points at a card of
the first one: CUSTOM card_focus {card_id} and no copy of it), new_card_no_highlight (the card is too far up:
the last answer draws a card with a new id and highlights nothing), capabilities: [card.focus] (sent as
forwardedProps.capabilities with every run, as a widget that can scroll to a card and highlight it does).
The assistant runs in-process (docs_ai.app.create_app) over the built docs (site/dist/llms-full.txt, or
DOCS_AI_CORPUS), with its own model (DOCS_AI_MODEL); build the site first so the corpus has the current pages.
The report goes to scripts/runs/ask-ai-<time>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
FOLDER = HERE / "evals" / "ask_ai"
RUNS = HERE / "scripts" / "runs"
KEYS = {"name", "ask", "turns", "runs", "says", "never_says", "no_repeated_cards", "first_turn_cards", "highlights_first_card",
        "new_card_no_highlight", "capabilities"}


def load(names: list[str] | None = None) -> list[dict]:
    out = []
    for p in sorted(FOLDER.glob("*.yaml")):
        q = yaml.safe_load(p.read_text()) or {}
        bad = sorted(set(q) - KEYS)
        if bad or not q.get("name") or not (q.get("ask") or q.get("turns")):
            raise ValueError(f"{p.name}: {'unknown key ' + bad[0] if bad else 'name and ask (or turns) are required'}")
        out.append(q)
    return [q for q in out if not names or q["name"] in names]


def turn(http, thread: str, history: list[dict], question: str, capabilities: list[str] | None = None) -> dict:
    """One question in a thread: the answer's text, its cards, its tool calls, and the assistant message to send
    back next time (with its toolCalls, as the widget keeps it)."""
    history.append({"id": str(uuid.uuid4()), "role": "user", "content": question})
    body = {"threadId": thread, "runId": str(uuid.uuid4()), "state": {}, "tools": [], "context": [],
            "forwardedProps": {"capabilities": list(capabilities)} if capabilities else {}, "messages": list(history)}
    text, cards, calls, mid = "", [], {}, None
    highlights: list[dict] = []
    results: dict[str, str] = {}
    with http.stream("POST", "/ask/run", json=body, headers={"Accept": "text/event-stream"}) as r:
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            e = json.loads(line[6:])
            t = e.get("type")
            if t == "TEXT_MESSAGE_CONTENT":
                text, mid = text + (e.get("delta") or ""), e.get("messageId")
            elif t == "TOOL_CALL_START":
                calls[e["toolCallId"]] = [e.get("toolCallName"), ""]
            elif t == "TOOL_CALL_ARGS" and e.get("toolCallId") in calls:
                calls[e["toolCallId"]][1] += e.get("delta") or ""
            elif t == "TOOL_CALL_RESULT":
                results[e.get("toolCallId")] = str(e.get("content") or "")
            elif t == "CUSTOM" and e.get("name") == "docs_card":
                cards.append(e.get("value"))
            elif t == "CUSTOM" and e.get("name") == "card_focus":
                highlights.append(e.get("value") or {})
            elif t == "RUN_ERROR":
                text += f"\nRUN_ERROR {e.get('message')}"
    for k, (n, raw) in calls.items():   # as the widget keeps it: each tool call its own assistant message, then its result
        history.append({"id": str(uuid.uuid4()), "role": "assistant", "content": "",
                        "toolCalls": [{"id": k, "type": "function", "function": {"name": n, "arguments": raw or "{}"}}]})
        history.append({"id": str(uuid.uuid4()), "role": "tool", "toolCallId": k, "content": results.get(k, "")})
    history.append({"id": mid or str(uuid.uuid4()), "role": "assistant", "content": text})   # the answer's text, apart
    return {"text": text, "cards": cards, "highlights": highlights, "calls": [(n, raw) for n, raw in calls.values()]}


def answer(http, question: str) -> str:
    """The whole answer as text: the message and everything its cards carry (code, pages, steps)."""
    t = turn(http, str(uuid.uuid4()), [], question)
    return t["text"] + "".join("\n" + json.dumps(c, ensure_ascii=False) for c in t["cards"])


def _body(card: dict) -> str:
    """A card without its id: two cards with the same content are the same card drawn twice."""
    return json.dumps({k: v for k, v in (card or {}).items() if k != "id"}, sort_keys=True)


def highlight_checks(q: dict, turns: list[dict]) -> list[dict]:
    """"Highlight, not a duplicate" (CPO, 2026-11-14): a card still in sight (the last 3 answers) is pointed at with
    card_focus {card_id}, never drawn again; one further up is drawn as a new card with a new id."""
    first, last, out = turns[0], turns[-1], []
    ids = [c.get("id") for c in first["cards"] if isinstance(c, dict) and c.get("id")]
    earlier = {c.get("id") for t in turns[:-1] for c in t["cards"] if isinstance(c, dict)}
    if q.get("highlights_first_card"):
        out.append({"check": "the first answer's card has an id", "ok": bool(ids)})
        out.append({"check": "points at the first answer's card (card_focus)",
                    "ok": any(h.get("card_id") in ids for h in last.get("highlights") or [])})
        out.append({"check": "draws no copy of the first answer's card",
                    "ok": not {_body(c) for c in first["cards"]} & {_body(c) for c in last["cards"]}})
    if q.get("new_card_no_highlight"):
        out.append({"check": "draws a card with a new id", "ok": any(isinstance(c, dict) and c.get("id") and c["id"] not in earlier for c in last["cards"])})
        out.append({"check": "highlights nothing", "ok": not last.get("highlights")})
    return out


def trace(asks: list[str], turns: list[dict]) -> list[dict]:
    """What each turn showed, for a failing run: the question, the text, each card (id, kind, caption, block ids) and
    each card_focus."""
    return [{"ask": a, "text": t["text"][:400],
             "cards": [{"id": c.get("id"), "kind": c.get("kind"), "caption": c.get("caption"),
                        "blocks": [b.get("id") for b in c.get("blocks") or [] if isinstance(b, dict)]} for c in t["cards"] if isinstance(c, dict)],
             "card_focus": [h.get("card_id") for h in t.get("highlights") or []]} for a, t in zip(asks, turns)]


def conversation(http, q: dict) -> tuple[str, list[dict], list[dict]]:
    """Several turns in one thread; the checks read the last answer. `no_repeated_cards`: the last turn shows no card
    (and makes no tool call) identical to one of an earlier turn."""
    thread, history, turns = str(uuid.uuid4()), [], []
    for ask in q["turns"]:
        turns.append(turn(http, thread, history, ask, q.get("capabilities")))
    last = turns[-1]
    text = last["text"] + "".join("\n" + json.dumps(c, ensure_ascii=False) for c in last["cards"])
    extra = []
    if q.get("no_repeated_cards"):
        before = [json.dumps(c, sort_keys=True) for t in turns[:-1] for c in t["cards"]]   # cards only: search_docs may repeat
        now = [json.dumps(c, sort_keys=True) for c in last["cards"]]
        extra.append({"check": "repeats no card of an earlier turn", "ok": not set(before) & set(now)})
    if q.get("first_turn_cards"):
        extra.append({"check": "the first answer shows a card", "ok": bool(turns[0]["cards"])})
    extra += highlight_checks(q, turns)
    return text, extra, trace(q["turns"], turns)


def check(q: dict, text: str) -> list[dict]:
    low = text.lower()
    out = [{"check": "says " + " / ".join(alts), "ok": any(a.lower() in low for a in alts)}
           for alts in ([x] if isinstance(x, str) else x for x in q.get("says") or [])]
    out += [{"check": f"never says {bad}", "ok": bad.lower() not in low} for bad in q.get("never_says") or []]
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--runs", type=int)
    a = ap.parse_args(argv)
    from fastapi.testclient import TestClient

    from docs_ai.app import create_app
    report = []
    with TestClient(create_app(per_minute=10_000, per_day=10_000, per_thread=100, site_per_day=100_000, origins=["*"])) as http:
        for q in load(a.names or None):
            n, res = a.runs or int(q.get("runs", 3)), []
            for i in range(n):
                text, extra, turns = conversation(http, q) if q.get("turns") else (answer(http, q["ask"]), [], [])
                checks = check(q, text) + extra
                res.append({"hit": all(c["ok"] for c in checks), "checks": checks, "answer": text[:4000]})
                if turns and not res[-1]["hit"]:   # a failing conversation keeps what every turn showed
                    res[-1]["turns"] = turns
                print(f"{'✅' if res[-1]['hit'] else '❌'} {q['name']} ({i + 1}/{n}) " + ", ".join(c["check"] for c in checks if not c["ok"]), flush=True)
            report.append({"name": q["name"], "ask": q.get("ask") or q["turns"], "runs": n, "hits": sum(r["hit"] for r in res), "results": res})
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"ask-ai-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "questions": report}, ensure_ascii=False, indent=1))
    for r in report:
        print(f"{r['name']:<36} {r['hits']}/{r['runs']}")
    print(f"report: {out}")
    return 0 if all(r["hits"] == r["runs"] for r in report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
