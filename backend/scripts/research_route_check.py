"""A short live pass over the public researcher demo route (docs_ai/research_demo.py), agent only, code checks.

    uv run python scripts/research_route_check.py --base http://127.0.0.1:8097 --models haiku luna --max-usd 0.10

For every public document set it asks two published questions (one short, one that needs a long answer) with
`depth: auto` on each model choice the server calls usable, and checks what a page would draw:
  - GET /research/sets lists exactly the public sets, each with its documents;
  - the run says which depth it chose (CUSTOM research {phase: decide}) and the choice fits the question;
  - an answer arrives, with sources that name documents of that set and carry an excerpt;
  - the run reports its tokens (run_stats), which this script prices from site/src/data/prices.json;
  - a set the server does not offer, and a model it does not have, are refused with 422.
The questions are the tuning ones the demo page already publishes (site/src/data/research-demo.json); no control
question is sent to a public route. It stops asking at --max-usd. Needs no key itself: the server holds the keys.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from harness_client import events  # noqa: E402
from research_depth import PUBLIC_SETS, call_usd  # noqa: E402

DEMO = HERE.parent / "site" / "src" / "data" / "research-demo.json"
RUNS = Path(__file__).parent / "runs"
DEEP_KINDS = ("compare", "why", "plan", "summary", "across")


def questions() -> list[dict]:
    """Two published questions a set: the first that needs a long answer and the first short one."""
    qs = json.loads(DEMO.read_text())["questions"]
    out = []
    for s in PUBLIC_SETS:
        mine = [q for q in qs if q["set"] == s]
        deep = next((q for q in mine if q.get("kind") in DEEP_KINDS), None)
        quick = next((q for q in mine if q.get("kind") not in DEEP_KINDS), None)
        out += [{"set": s, "question": q["question"], "expects": d} for q, d in ((quick, "quick"), (deep, "deep")) if q]
    return out


def ask(http: httpx.Client, q: dict, model: str | None) -> dict:
    body = {"threadId": str(uuid.uuid4()), "runId": str(uuid.uuid4()), "messages": [{"id": "u1", "role": "user", "content": q["question"]}],
            "state": {"set": q["set"]}, "tools": [], "context": [], "forwardedProps": {"depth": "auto", **({"model": model} if model else {})}}
    t0 = time.perf_counter()
    rec: dict = {"set": q["set"], "question": q["question"], "expects": q["expects"], "model": model, "text": "", "sources": [], "depth": "",
                 "first_word_s": None, "steps": 0, "error": None, "tokens": {}, "model_id": ""}
    try:
        for e in events(http, "/research/run", body):
            t, name, v = e.get("type"), e.get("name"), e.get("value") or {}
            if t == "TEXT_MESSAGE_CONTENT":
                if rec["first_word_s"] is None:
                    rec["first_word_s"] = round(time.perf_counter() - t0, 2)
                rec["text"] += e.get("delta") or ""
            elif t == "TOOL_CALL_START":
                rec["steps"] += 1
            elif t == "RUN_ERROR":
                rec["error"] = str(e.get("message"))[:300]
            elif name == "research" and v.get("phase") == "decide":
                rec["depth"], rec["why"] = str(v.get("depth")), str(v.get("why"))
            elif name == "sources":
                rec["sources"] = list(v.get("items") or [])
            elif name == "model":
                rec["model_id"] = str(v.get("model") or v.get("id") or "")
            elif name == "run_stats":
                rec["tokens"] = dict(v.get("tokens") or {})
                rec["model_id"] = rec["model_id"] or next((str(m.get("model")) for m in v.get("models") or [] if m.get("model")), "")
    except httpx.HTTPError as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"[:300]
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    tok = rec["tokens"]
    try:
        rec["usd"] = round(call_usd({"model": rec["model_id"], "input": int(tok.get("input") or 0), "output": int(tok.get("output") or 0),
                                     "cache_read": int(tok.get("cache_read") or 0), "cache_creation": int(tok.get("cache_write") or 0)},
                                    "gpt-6-luna" if model == "luna" else "claude-haiku-5-5"), 5)
    except SystemExit:
        rec["usd"] = None
    return rec


def checks(rec: dict, docs: set[str]) -> list[str]:
    """What is wrong with one answer, in plain words (empty when nothing is)."""
    why = []
    if rec["error"]:
        why.append(f"run error: {rec['error']}")
    if not rec["text"].strip():
        why.append("no answer")
    if rec["depth"] not in ("quick", "deep"):
        why.append("the run did not say which depth it chose")
    elif rec["depth"] != rec["expects"]:
        why.append(f"chose {rec['depth']} for a question that needs a {rec['expects']} answer")
    if rec["text"].strip() and not rec["sources"]:
        why.append("no sources")
    named = {str(s.get("title") or s.get("document") or "") for s in rec["sources"]}
    if named and not named & docs and not any(n in d or d in n for n in named for d in docs):
        why.append(f"sources name no document of the set: {sorted(named)[:3]}")
    if rec["sources"] and not any(str(s.get("quote") or s.get("excerpt") or "").strip() for s in rec["sources"]):
        why.append("no source carries an excerpt")
    if not rec["tokens"]:
        why.append("no token counts (run_stats)")
    return why


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="the host that serves /research (a local stand; never the public site for a loop of runs)")
    ap.add_argument("--models", nargs="*", default=[], help="model choices to ask on (default: every usable one the server lists)")
    ap.add_argument("--max-usd", type=float, required=True)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    problems: list[str] = []
    with httpx.Client(base_url=a.base, timeout=180, headers={"X-Demo-Visitor": f"qa-{uuid.uuid4().hex[:8]}"}) as http:
        sets = http.get("/research/sets").json()
        listed = {s["id"]: s for s in sets.get("sets") or []}
        if set(listed) != set(PUBLIC_SETS):
            problems.append(f"/research/sets lists {sorted(listed)}, the public sets are {sorted(PUBLIC_SETS)}")
        if any(not s.get("documents") for s in listed.values()):
            problems.append("a set is listed without its documents")
        choices = (http.get("/agent/models").json().get("choices") or []) if http.get("/agent/models").status_code == 200 else []
        usable = [c["name"] for c in choices if c.get("usable", True)]
        models = [m for m in (a.models or usable) if m in usable] or [None]
        skipped = [m for m in a.models if m not in usable]
        if skipped:
            print(f"not usable on this server (no key?): {', '.join(skipped)}")
        bad_set = http.post("/research/run", json={"threadId": "t", "runId": "r", "messages": [{"id": "u", "role": "user", "content": "hello"}],
                                                   "state": {"set": "northwind_insurance"}, "tools": [], "context": [], "forwardedProps": {}})
        if bad_set.status_code != 422:
            problems.append(f"a set that is not public was not refused (HTTP {bad_set.status_code})")
        bad_model = http.post("/research/run", json={"threadId": "t", "runId": "r", "messages": [{"id": "u", "role": "user", "content": "hello"}],
                                                     "state": {"set": next(iter(PUBLIC_SETS))}, "tools": [], "context": [], "forwardedProps": {"model": "no-such-model"}})
        if bad_model.status_code != 422:
            problems.append(f"an unknown model choice was not refused (HTTP {bad_model.status_code})")
        results, spent = [], 0.0
        for model in models:
            for q in questions():
                if spent >= a.max_usd:
                    results.append({**q, "model": model, "skipped": "the stop sum was reached"})
                    continue
                http.headers["X-Demo-Visitor"] = f"qa-{uuid.uuid4().hex[:8]}"   # the demo counts messages per visitor
                rec = ask(http, q, model)
                rec["why"] = checks(rec, {str(d.get("id") or d.get("title")) for d in listed.get(q["set"], {}).get("documents") or []} |
                                    {str(d.get("title")) for d in listed.get(q["set"], {}).get("documents") or []})
                spent += rec.get("usd") or 0
                results.append(rec)
                print(f"{'✅' if not rec['why'] else '❌'} {model or 'default':<6} {q['set']:<16} {q['expects']:<5} -> {rec['depth'] or '?':<5} "
                      f"{rec['seconds']:>5}s first {rec['first_word_s']}s  {len(rec['sources'])} sources  ${rec.get('usd')}  {'; '.join(rec['why'])[:140]}", flush=True)
    done = [r for r in results if "skipped" not in r]
    ok = sum(1 for r in done if not r["why"])
    print(f"\n{ok} of {len(done)} answers pass every check; spent ${spent:.4f}" + (f"; {len(results) - len(done)} not asked (stop sum)" if len(results) > len(done) else ""))
    print("\n".join("route: " + p for p in problems) if problems else "route: the sets, the refusals of an unknown set and model are right")
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"research-route-{datetime.now():%Y%m%d-%H%M%S}{'-' + a.label if a.label else ''}.json"
    out.write_text(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "base": a.base, "problems": problems, "usd": round(spent, 5), "results": results},
                              ensure_ascii=False, indent=1))
    print(f"report: {out}")
    return 0 if ok == len(done) and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
