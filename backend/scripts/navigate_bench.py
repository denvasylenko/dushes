"""Navigate benchmark for the docs: three counts by code from a site-probe journal (no model judges).

    uv run python scripts/navigate_bench.py <probe.jsonl> --commit 0edae85 --model "GPT-6 Luna" \
        --date 2026-11-19 --report <where the journal came from>

Writes site/src/data/benchmarks/navigate.json. Rows:
  no_such_page         lines of the "unknown" group (an order for a page the site does not have): passed = nothing opened;
  questions_open_page  lines whose gold is no move ("answer" / "agent", the unknown lines included): passed = nothing opened;
  orders_refused       lines whose gold is a move: passed = the tool did not answer "Not opened:".
"""
import argparse
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[2] / "site/src/data/benchmarks/navigate.json"


def moved(t):
    for d in t.get("directives") or []:
        if not isinstance(d, dict):
            continue
        if d.get("type") == "navigate" and d.get("path"):
            return True
        if any(d.get(k) for k in ("target", "section", "part", "tab")) or d.get("reveal"):
            return True
    return bool(t.get("card"))


def refused(t):
    return any(isinstance(x, dict) and str(x.get("result", "")).startswith("Not opened:") for x in t.get("tools") or [])


def golds(r):
    g = r["gold"]
    if isinstance(g, list) and len(g) == len(r["turns"]) and len(r["turns"]) > 1:
        return g
    return [g] * len(r["turns"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("journal")
    ap.add_argument("--commit", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--layer", action="store_true", help="the decision model (layer) was on")
    a = ap.parse_args()
    c = {k: [0, 0] for k in ("no_such_page", "questions_open_page", "orders_refused")}
    for line in open(a.journal):
        r = json.loads(line)
        for t, g in zip(r["turns"], golds(r)):
            if r.get("group") == "unknown":
                c["no_such_page"][1] += 1
                c["no_such_page"][0] += not moved(t)
            if g in ("answer", "agent"):
                c["questions_open_page"][1] += 1
                c["questions_open_page"][0] += not moved(t)
            elif isinstance(g, list) and len(g) == 2 and isinstance(g[0], str) and g[0].startswith("/"):
                c["orders_refused"][1] += 1
                c["orders_refused"][0] += not refused(t)
    labels = {
        "no_such_page": "An order for a page the site does not have opens nothing",
        "questions_open_page": "Questions that open a page",
        "orders_refused": "Orders refused",
    }
    rows = []
    for k, (ok, n) in c.items():
        row = {"id": k, "label": labels[k], "passed": ok, "total": n}
        if k != "no_such_page":
            row["failed"] = n - ok  # the docs show these two as "failed of total" (0/70, 0/140)
        rows.append(row)
    data = {"source": "backend/scripts/navigate_bench.py", "measured_at": a.date, "commit": a.commit,
            "model": a.model, "layer": a.layer, "measured": True, "report": a.report, "rows": rows}
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=True) + "\n")
    print(json.dumps(data, indent=1))


if __name__ == "__main__":
    main()
