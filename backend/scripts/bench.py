"""Live speed benchmark against a running formguide server (the demo, or a hosted one).

    uv run python scripts/bench.py                                  # all scenarios once, http://127.0.0.1:8000
    uv run python scripts/bench.py --repeat 3 --max-ttft 4 --max-turn 30
    uv run python scripts/bench.py --base https://formguide-demo.fly.dev --user demo --password ...
    uv run python scripts/bench.py --prices prices.json             # {"input": 5, "output": 25, "cache_read": 0.5} per 1M tokens

Each scenario is one user turn on a fresh thread: cards are accepted and questions answered with
their first option, as a user would; the time the "user" takes is not counted. The numbers come from
the server's own `run_stats` events, so they are the server's view (network not included).
Prints a table (median and p90 per scenario) and writes scripts/bench-<time>.json. Exits with 1 when
a threshold is exceeded, so it can gate a release.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

SCENARIOS: list[tuple[str, str, str]] = [   # name, form, message
    ("question", "loan_application", "Where do I start?"),
    ("fill", "loan_application", "My name is Anna Petrova, born 12 April 1990."),
    ("choice", "loan_application", "I'd like to apply for a loan, help me pick the type."),
    ("documents", "loan_application", "What is the interest rate for a car loan?"),
    ("booking", "barber_booking", "Book me a haircut and beard trim next Tuesday around 3pm."),
]


class Client:
    def __init__(self, base: str, auth: tuple[str, str] | None):
        self.http = httpx.Client(base_url=base, timeout=300, auth=auth)
        self.forms: dict[str, dict] = {}

    def form(self, form_id: str) -> dict:
        if form_id not in self.forms:
            f = self.http.get("/java/form", params={"form_id": form_id}).raise_for_status().json()
            h = self.http.post("/agent/layouts", json={"jsx": f["jsx"], "form_id": form_id, "domain": f["domain"]})
            self.forms[form_id] = {**f, "jsx_hash": h.raise_for_status().json()["jsx_hash"]}
        return self.forms[form_id]

    def run(self, body: dict) -> tuple[dict | None, dict | None]:
        """One run: (its run_stats, the interrupt it ended with, if any)."""
        stats = interrupt = None
        with self.http.stream("POST", "/agent/run", json=body) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data: "):
                    continue
                e = json.loads(line[6:])
                if e.get("name") == "run_stats":
                    stats = e["value"]
                elif e.get("name") == "on_interrupt":
                    interrupt = json.loads(e["value"]) if isinstance(e["value"], str) else e["value"]
                elif e["type"] == "RUN_ERROR":
                    raise RuntimeError(e.get("message"))
        return stats, interrupt

    def turn(self, form_id: str, message: str) -> list[dict]:
        """A user turn, with cards answered automatically: the stats of each of its runs."""
        f = self.form(form_id)
        config, thread = f["config"], str(uuid.uuid4())
        state = {"config": config, "jsx_hash": f["jsx_hash"], "form_id": form_id,
                 "ui": {"activeTabs": {}, "openAccordions": [], "focused": None, "now": datetime.now().strftime("%Y-%m-%d %A %H:%M")}}
        body: dict[str, Any] = {"threadId": thread, "messages": [{"role": "user", "content": message}], "state": state}
        runs = []
        for _ in range(6):            # a turn rarely needs more than a couple of cards
            stats, it = self.run(body)
            if stats:
                runs.append(stats)
            if not it:
                break
            if it.get("type") == "set_fields":
                config = self.http.post("/java/event", json={"form_id": form_id, "state": config["state"],
                                                             "changes": {c["name"]: c["value"] for c in it["changes"]}}).json()
                resume: dict = {"accepted": True, "config": config}
            elif it.get("type") == "ask" and it.get("options"):
                resume = {"answer": {"ids": [it["options"][0]["id"]]}}
            else:
                resume = {"accepted": False}
            body = {"threadId": thread, "state": {**state, "config": config}, "forwardedProps": {"command": {"resume": resume}}}
        return runs


def summarize(runs: list[dict], prices: dict | None) -> dict:
    ttft = next((r["ttft_ms"] for r in runs if r.get("ttft_ms") is not None), None)
    tok = {k: sum((r["tokens"].get(k) or 0) for r in runs) for k in ("input", "output", "cache_read")}
    out = {"ttft_ms": ttft, "turn_ms": sum(r["total_ms"] for r in runs), "model_ms": sum(r["model_ms"] for r in runs),
           "tool_ms": sum(r["tool_ms"] for r in runs), "runs": len(runs),
           "tools": sum(len(r["tools"]) for r in runs), "model_calls": sum(len(r["models"]) for r in runs),
           "tokens": tok, "cache_hit_rate": round(tok["cache_read"] / tok["input"], 3) if tok["input"] else None}
    if prices:
        fresh = max(0, tok["input"] - tok["cache_read"])
        out["cost_usd"] = round((fresh * prices.get("input", 0) + tok["cache_read"] * prices.get("cache_read", 0)
                                 + tok["output"] * prices.get("output", 0)) / 1e6, 4)
    return out


def pct(values: list[float], p: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    return vals[min(len(vals) - 1, round(p * (len(vals) - 1)))]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--user", default="demo")
    ap.add_argument("--password")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", nargs="*", help="scenario names")
    ap.add_argument("--max-ttft", type=float, help="seconds: fail when a median time to first token is above")
    ap.add_argument("--max-turn", type=float, help="seconds: fail when a median turn time is above")
    ap.add_argument("--prices", type=Path, help='JSON per 1M tokens: {"input": .., "output": .., "cache_read": ..}')
    a = ap.parse_args(argv)
    prices = json.loads(a.prices.read_text()) if a.prices else None
    client = Client(a.base, (a.user, a.password) if a.password else None)

    results: dict[str, list[dict]] = {}
    for name, form_id, message in SCENARIOS:
        if a.only and name not in a.only:
            continue
        for i in range(a.repeat):
            t = time.perf_counter()
            try:
                s = summarize(client.turn(form_id, message), prices)
            except Exception as e:  # noqa: BLE001
                s = {"error": f"{type(e).__name__}: {e}"}
            s["wall_ms"] = round((time.perf_counter() - t) * 1000)
            results.setdefault(name, []).append(s)
            print(f"  {name} #{i + 1}: " + (s.get("error") or f"first token {s['ttft_ms']} ms, turn {s['turn_ms']} ms"), flush=True)

    rows, failed = [], []
    print(f"\n{'scenario':<11}{'ttft med':>10}{'ttft p90':>10}{'turn med':>10}{'turn p90':>10}{'tools':>7}{'tokens in/out':>16}{'cache':>7}{'cost':>9}")
    for name, items in results.items():
        ok = [x for x in items if "error" not in x]
        if not ok:
            print(f"{name:<11} all runs failed: {items[0]['error']}")
            failed.append(f"{name}: failed")
            continue
        ttft = [x["ttft_ms"] for x in ok]
        turn = [x["turn_ms"] for x in ok]
        med_ttft = statistics.median([v for v in ttft if v is not None]) if any(v is not None for v in ttft) else None
        med_turn = statistics.median(turn)
        tin = round(statistics.mean(x["tokens"]["input"] for x in ok))
        tout = round(statistics.mean(x["tokens"]["output"] for x in ok))
        cache = statistics.mean(x["cache_hit_rate"] or 0 for x in ok)
        cost = statistics.mean(x.get("cost_usd", 0) for x in ok) if prices else None
        s = lambda ms: "-" if ms is None else f"{ms / 1000:.1f}s"  # noqa: E731
        print(f"{name:<11}{s(med_ttft):>10}{s(pct(ttft, .9)):>10}{s(med_turn):>10}{s(pct(turn, .9)):>10}"
              f"{statistics.mean(x['tools'] for x in ok):>7.1f}{f'{tin}/{tout}':>16}{cache:>6.0%}"
              f"{(f'${cost:.3f}' if cost is not None else '-'):>9}")
        rows.append({"scenario": name, "ttft_median_ms": med_ttft, "ttft_p90_ms": pct(ttft, .9), "turn_median_ms": med_turn,
                     "turn_p90_ms": pct(turn, .9), "runs": items})
        if a.max_ttft and med_ttft is not None and med_ttft > a.max_ttft * 1000:
            failed.append(f"{name}: first token {med_ttft / 1000:.1f}s > {a.max_ttft}s")
        if a.max_turn and med_turn > a.max_turn * 1000:
            failed.append(f"{name}: turn {med_turn / 1000:.1f}s > {a.max_turn}s")

    out = Path(__file__).parent / f"bench-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"base": a.base, "repeat": a.repeat, "prices": prices, "scenarios": rows}, indent=1))
    print(f"\nsaved {out}")
    if failed:
        print("FAILED:\n  " + "\n  ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
