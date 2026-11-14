"""The Site agent (Dushes) navigation benchmark: one message per phrase, on a fresh visit, and where the site went.

    uv run python scripts/site_bench.py                         # evals/site/nav_demo.json against the demo server
    uv run python scripts/site_bench.py --agent-model openai:gpt-5-mini   # in-process, another agent model
    uv run python scripts/site_bench.py --offline               # a scripted model: the plumbing only

A phrase set (evals/site/<set>.json, from R&D) holds {site, start, phrases: [{text, lang, kind, expect}]}; expect is
{path, tab|accordion|section?} or "no navigation". Each phrase is sent once from the set's start page; the first
navigate directive of the run is compared with expect:
  right      the expected page (and its tab, accordion or section when one is expected)
  page only  the expected page, another or no part
  wrong      another page
  missed     no navigation where one was expected
  needless   a navigation where "no navigation" was expected (the error R&D measured: 9 of 20)
  quiet      no navigation, as expected
Timing per phrase: wall time to the navigate directive and to the first word of the answer.
The report goes to scripts/runs/site-<time>.json and a summary is printed by language and kind.
Only the "main" site (demo/site.yaml) runs here; the cabinet set needs the Herefront cabinet's site map.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from harness_client import BASE, RUNS  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
SETS = HERE / "evals" / "site"


def one(http: httpx.Client, prefix: str, start: str, text: str) -> dict:
    """One message on a fresh visit: the first navigate directive, the reply, the times."""
    body = {"threadId": str(uuid.uuid4()), "runId": str(uuid.uuid4()), "state": {"page": {"path": start, "title": ""}},
            "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": text}], "tools": [], "context": [], "forwardedProps": {}}
    t0, nav, first, reply, tools, err = time.perf_counter(), None, None, "", [], None
    try:
        with http.stream("POST", f"{prefix}/run", json=body) as r:
            for line in r.iter_lines():
                if not line.startswith("data: "):
                    continue
                e = json.loads(line[6:])
                t = time.perf_counter() - t0
                if e.get("type") == "TEXT_MESSAGE_CONTENT":
                    first = first if first is not None else t
                    reply += e.get("delta") or ""
                elif e.get("type") == "TOOL_CALL_START":
                    tools.append(e.get("toolCallName"))
                elif e.get("name") == "site_directive" and (e.get("value") or {}).get("type") == "navigate" and nav is None:
                    nav = {**e["value"], "at_s": round(t, 2)}
                elif e.get("type") == "RUN_ERROR":
                    err = str(e.get("message"))
    except httpx.HTTPError as ex:
        err = f"{type(ex).__name__}: {ex}"
    return {"nav": nav, "first_word_s": round(first, 2) if first is not None else None, "total_s": round(time.perf_counter() - t0, 2),
            "reply": reply.strip()[:400], "tools": tools, "error": err}


def verdict(expect: dict | str, nav: dict | None) -> str:
    if expect == "no navigation":
        return "needless" if nav else "quiet"
    if not nav:
        return "missed"
    if nav.get("path") != expect.get("path"):
        return "wrong"
    part = expect.get("tab") or expect.get("accordion") or expect.get("section")
    got = nav.get("tab") or nav.get("section")
    return "right" if not part or part == got else "page only"


def summary(rows: list[dict]) -> dict:
    nav = [r for r in rows if r["expect"] != "no navigation"]
    quiet = [r for r in rows if r["expect"] == "no navigation"]

    def rate(xs, ok):
        return round(sum(r["verdict"] in ok for r in xs) / len(xs), 3) if xs else None
    out = {"phrases": len(rows), "right": rate(nav, {"right"}), "right_page": rate(nav, {"right", "page only"}),
           "wrong": rate(nav, {"wrong"}), "missed": rate(nav, {"missed"}), "needless": rate(quiet, {"needless"}),
           "errors": sum(1 for r in rows if r["error"]),
           "to_navigate_s": statistics.median([r["nav"]["at_s"] for r in rows if r["nav"]]) if any(r["nav"] for r in rows) else None,
           "first_word_s": statistics.median([r["first_word_s"] for r in rows if r["first_word_s"] is not None])
           if any(r["first_word_s"] is not None for r in rows) else None}
    for key in ("lang", "kind"):
        groups = defaultdict(list)
        for r in rows:
            groups[r[key]].append(r)
        out[f"by_{key}"] = {g: {"n": len(v), "ok": round(sum(x["verdict"] in ("right", "quiet") for x in v) / len(v), 3)}
                            for g, v in sorted(groups.items())}
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="The Site agent navigation benchmark.")
    ap.add_argument("set", nargs="?", default="nav_demo", help="a phrase set in evals/site/ (default nav_demo)")
    ap.add_argument("--agent-model", help="run the demo in-process with this agent model (see evals.py --agent-model)")
    ap.add_argument("--offline", action="store_true", help="a scripted model, in-process: the plumbing only")
    ap.add_argument("--limit", type=int, help="the first N phrases only")
    a = ap.parse_args(argv)
    data = json.loads((SETS / f"{a.set}.json").read_text())
    if data.get("site") != "main":
        print(f"the {a.set} set is for the {data.get('site')} site map, which is not in this repository")
        return 2
    import evals
    if a.offline:
        http = evals.offline_client(Path(tempfile.mkdtemp(prefix="formguide-site-")))
    elif a.agent_model:
        http = evals.agent_client(Path(tempfile.mkdtemp(prefix="formguide-site-")), a.agent_model)
    else:
        http = httpx.Client(base_url=BASE, timeout=300)
    rows = []
    for p in data["phrases"][: a.limit or None]:
        r = one(http, "/site", data.get("start", "/"), p["text"])
        r.update({"text": p["text"], "lang": p["lang"], "kind": p["kind"], "expect": p["expect"],
                  "verdict": verdict(p["expect"], r["nav"])})
        rows.append(r)
        print(f"{r['verdict']:<10} {p['lang']} {p['kind']:<15} {json.dumps(p['text'], ensure_ascii=False)[:60]}", flush=True)
    s = summary(rows)
    report = {"at": datetime.now().isoformat(timespec="seconds"), "set": a.set, "agent_model": a.agent_model,
              "offline": a.offline, "summary": s, "phrases": rows}
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"site-{datetime.now():%Y%m%d-%H%M%S}{'-offline' if a.offline else ''}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in s.items() if not k.startswith("by_")}, indent=1))
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
