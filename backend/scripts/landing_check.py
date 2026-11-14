"""A check of the public landing demo (docs_ai/host.py), in-process: the per-visitor limit and a few live turns.

    uv run python scripts/landing_check.py            # needs ANTHROPIC_API_KEY (the live turns and the 10 allowed runs)

1. The limit: one X-Demo-Visitor sends 11 messages to /agent/run on landing_loan (its hash from
   GET /agent/layouts/landing_loan); the first 10 are served, the 11th gets 429 {code: demo_limit, reason: visitor}.
2. Live turns: three messages on landing_loan (a start, an off-topic question, the loan's numbers), judged for
   brevity and for staying on the form.
The report goes to scripts/runs/landing-<time>.json and the conversation to scripts/runs/landing-turns.txt.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).parent))
from harness_client import RUNS, events  # noqa: E402

FORM = "landing_loan"
CONFIG = HERE / "demo" / "landing" / f"{FORM}.config.json"   # the landing page's own props and state
TURNS = ["Hi! I'd like a car loan for a Tesla.", "By the way, what's the weather in Lisbon tomorrow?",
         "OK. 30 000 euros over 5 years, please."]
RUBRIC = """You judge one short conversation on a public demo of a loan form assistant. Score 0 to 10 for:
- brevity: each answer is short (1-3 sentences), no lists of everything the form has (up to 4 points);
- staying on the form: off-topic questions get one polite sentence and the talk comes back to the form; values the
  user gives are proposed for the form's fields on a card (up to 4 points);
- tone and language: the user's language, friendly (up to 2 points).
Name every point you take off with the sentence that caused it."""


def config() -> dict:
    return json.loads(CONFIG.read_text())


def body(thread: str, text: str, h: str, cfg: dict) -> dict:
    return {"threadId": thread, "runId": str(uuid.uuid4()), "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": text}],
            "state": {"config": cfg, "jsx_hash": h, "form_id": FORM, "ui": {"activeTabs": {}, "openAccordions": [], "focused": None}},
            "tools": [], "context": [], "forwardedProps": {}}


def main() -> int:
    from fastapi.testclient import TestClient

    from docs_ai.host import app   # the public host: the demo, its limits, Ask AI
    http = TestClient(app)
    h = http.get(f"/agent/layouts/{FORM}").json()["jsx_hash"]
    cfg, out = config(), {"at": datetime.now().isoformat(timespec="seconds")}

    # 1. the visitor limit: fresh visitor and thread ids, so the day's other numbers do not interfere
    visitor = "qa" + uuid.uuid4().hex[:12]
    codes, last = [], None
    for i in range(11):
        thread = str(uuid.uuid4())   # a new conversation each time: the per-thread cap (15) is not what is measured
        with http.stream("POST", "/agent/run", json=body(thread, f"Hello {i + 1}", h, cfg),
                         headers={"X-Demo-Visitor": visitor}) as r:
            codes.append(r.status_code)
            raw = r.read()
            if r.status_code == 429:
                last = json.loads(raw)
    limit_ok = codes[:10] == [200] * 10 and codes[10] == 429 and (last or {}).get("code") == "demo_limit" \
        and (last or {}).get("reason") == "visitor"
    out["limit"] = {"ok": limit_ok, "codes": codes, "refusal": last}
    print(f"{'✅' if limit_ok else '❌'} visitor limit: {codes} {json.dumps(last)[:160] if last else ''}")

    # 2. live turns, judged
    thread, visitor, log = str(uuid.uuid4()), "qa" + uuid.uuid4().hex[:12], []
    for text in TURNS:
        log.append(f"👤 {text}")
        texts: dict[str, str] = {}
        calls: dict[str, str] = {}
        for e in events(_with_header(http, visitor), "/agent/run", body(thread, text, h, cfg)):
            if e["type"] == "TEXT_MESSAGE_CONTENT":
                texts[e["messageId"]] = texts.get(e["messageId"], "") + e["delta"]
            elif e["type"] == "TOOL_CALL_START":
                calls[e["toolCallId"]] = e["toolCallName"]
            elif e.get("name") == "on_interrupt":
                v = json.loads(e["value"]) if isinstance(e["value"], str) else e["value"]
                if v.get("changes"):
                    log.append("   🃏 card: " + "; ".join(f"{c.get('label')} = {c.get('display')}" for c in v["changes"]))
                break   # the visitor reads the card; the next message answers in prose
        log += [f"🤖 {t.strip()}" for t in texts.values() if t.strip()] + [f"   ⚙ {c}" for c in calls.values()]
    transcript = "\n".join(log)
    RUNS.mkdir(exist_ok=True)
    (RUNS / "landing-turns.txt").write_text(transcript)
    from evals import Verdict
    from formguide.models import structured
    from formguide.models import build_model
    judge = build_model(os.environ.get("LANDING_JUDGE", "anthropic:claude-sonnet-5-5"))   # a fixed judge, not the agent's model
    v = structured(judge, Verdict).invoke([("human", f"{RUBRIC}\n\nThe conversation:\n{transcript}")])
    out["turns"] = {"score": v.score, "lost": [x.model_dump() for x in v.lost], "transcript": "scripts/runs/landing-turns.txt"}
    print(f"live turns: {v.score} / 10")
    for x in v.lost:
        print(f"  -{x.points} {x.reason}")
    path = RUNS / f"landing-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"report: {path}")
    return 0 if limit_ok else 1


def _with_header(http, visitor: str):
    """The TestClient with the visitor header on every request (events() posts without headers)."""
    http.headers["X-Demo-Visitor"] = visitor
    return http


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is needed (the 10 allowed runs and the live turns call the model).")
        sys.exit(2)
    sys.exit(main())
