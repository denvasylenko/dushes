"""Load: many visitors at once on a formguide server, at steps of concurrency. Local or a separate app only, never
production.

    uv run python scripts/load.py                                   # steps 1 5 10 20 40, the demo on :8000
    uv run python scripts/load.py --steps 1 5 --turns 2 --base http://127.0.0.1:8090
    uv run python scripts/load.py --prices ../site/src/data/prices.json --pid 12345   # cost, and the server's memory

Each visitor is a fresh thread on the loan form that sends `--turns` short messages (a question, a fill, a choice),
accepting the field card the way a user would (the next message goes with the form unchanged; the card's resume is
not sent, so a turn is one run). Per step: p50 and p95 of the time to the first word and of the whole turn (wall time
at the client), the error rate (HTTP errors, RUN_ERROR, 429 counted apart), the tokens and the cost from the
server's run_stats, and the server's resident memory when --pid is given. The bar: p95 to the first word <= 4 s at
every step with the production model. The report goes to scripts/runs/load-<time>.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from harness_client import RUNS  # noqa: E402

FORM = "loan_application"
MESSAGES = ["Where do I start?", "My name is Anna Petrova, born 12 April 1990.", "What is the interest rate for a car loan?",
            "I'd like a consumer loan of 500 000 for 3 years."]
BAR_TTFT_S = 4.0


async def visitor(http: httpx.AsyncClient, form: dict, turns: int) -> list[dict]:
    thread, out = str(uuid.uuid4()), []
    for i in range(turns):
        state = {"config": form["config"], "jsx_hash": form["jsx_hash"], "form_id": FORM,
                 "ui": {"activeTabs": {}, "openAccordions": [], "focused": None}}
        body = {"threadId": thread, "runId": str(uuid.uuid4()), "state": state, "tools": [], "context": [], "forwardedProps": {},
                "messages": [{"id": str(uuid.uuid4()), "role": "user", "content": MESSAGES[i % len(MESSAGES)]}]}
        t0, first, stats, status, err = time.perf_counter(), None, None, None, None
        try:
            async with http.stream("POST", "/agent/run", json=body) as r:
                status = r.status_code
                if r.status_code != 200:
                    err = f"HTTP {r.status_code}"
                    await r.aread()
                else:
                    async for line in r.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        e = json.loads(line[6:])
                        if e.get("type") == "TEXT_MESSAGE_CONTENT" and first is None:
                            first = time.perf_counter() - t0
                        elif e.get("type") == "RUN_ERROR":
                            err = str(e.get("message"))[:200]
                        elif e.get("name") == "run_stats":
                            stats = e.get("value")
        except httpx.HTTPError as ex:
            err = f"{type(ex).__name__}: {ex}"[:200]
        out.append({"ttft_s": first, "turn_s": time.perf_counter() - t0, "status": status, "error": err,
                    "models": (stats or {}).get("models") or [], "tokens": (stats or {}).get("tokens") or {}})
    return out


def pct(v: list[float], p: float) -> float | None:
    v = sorted(x for x in v if x is not None)
    return round(v[min(len(v) - 1, round(p * (len(v) - 1)))], 2) if v else None


def rss_mb(pid: int | None) -> float | None:
    if not pid:
        return None
    try:
        return round(int(subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()) / 1024, 1)
    except (ValueError, OSError):
        return None


async def step(base: str, n: int, turns: int, prices: dict | None, pid: int | None) -> dict:
    async with httpx.AsyncClient(base_url=base, timeout=180, limits=httpx.Limits(max_connections=n + 4)) as http:
        f = (await http.get("/java/form", params={"form_id": FORM})).raise_for_status().json()
        reg = (await http.post("/agent/layouts", json={"jsx": f["jsx"], "form_id": FORM, "domain": f["domain"]})).raise_for_status().json()
        form = {"config": f["config"], "jsx_hash": reg["jsx_hash"]}
        mem0 = rss_mb(pid)
        t0 = time.perf_counter()
        runs = [r for v in await asyncio.gather(*(visitor(http, form, turns) for _ in range(n))) for r in v]
        wall = time.perf_counter() - t0
    ok = [r for r in runs if not r["error"]]
    cost = None
    if prices:
        from bench import call_cost, price_for
        cost = round(sum(call_cost(m, p) for r in runs for m in r["models"]
                         if (p := price_for(prices, m.get("model"), "claude-haiku-5-5"))), 4)
    p95 = pct([r["ttft_s"] for r in ok], 0.95)
    return {"visitors": n, "turns": len(runs), "wall_s": round(wall, 1),
            "ttft_p50_s": pct([r["ttft_s"] for r in ok], 0.5), "ttft_p95_s": p95,
            "turn_p50_s": pct([r["turn_s"] for r in ok], 0.5), "turn_p95_s": pct([r["turn_s"] for r in ok], 0.95),
            "errors": sum(1 for r in runs if r["error"] and r["status"] != 429), "limited_429": sum(1 for r in runs if r["status"] == 429),
            "error_samples": sorted({r["error"] for r in runs if r["error"]})[:3],
            "tokens_in": sum(int(r["tokens"].get("input") or 0) for r in runs), "tokens_out": sum(int(r["tokens"].get("output") or 0) for r in runs),
            "cost_usd": cost, "rss_mb_before": mem0, "rss_mb_after": rss_mb(pid), "bar_ok": p95 is not None and p95 <= BAR_TTFT_S}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--steps", type=int, nargs="+", default=[1, 5, 10, 20, 40])
    ap.add_argument("--turns", type=int, default=3, help="messages per visitor")
    ap.add_argument("--prices", type=Path, help="site/src/data/prices.json: the cost of each step")
    ap.add_argument("--pid", type=int, help="the server process: its memory before and after each step")
    a = ap.parse_args(argv)
    if any(h in a.base for h in ("fly.dev", "dushes-ai")):
        print("refused: load is never run against production (use a local server or a separate app)")
        return 2
    prices = json.loads(a.prices.read_text()) if a.prices else None
    rows = []
    for n in a.steps:
        r = asyncio.run(step(a.base, n, a.turns, prices, a.pid))
        rows.append(r)
        print(f"{n:>3} visitors: first word p50 {r['ttft_p50_s']}s p95 {r['ttft_p95_s']}s | turn p50 {r['turn_p50_s']}s "
              f"p95 {r['turn_p95_s']}s | errors {r['errors']} 429 {r['limited_429']} | ${r['cost_usd']} | "
              f"rss {r['rss_mb_before']}->{r['rss_mb_after']} MB {'✅' if r['bar_ok'] else '❌'}", flush=True)
    RUNS.mkdir(exist_ok=True)
    out = RUNS / f"load-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "base": a.base, "turns": a.turns,
                               "bar_ttft_p95_s": BAR_TTFT_S, "steps": rows}, indent=1))
    print(f"report: {out}; total ${round(sum(r['cost_usd'] or 0 for r in rows), 4)}")
    return 0 if all(r["bar_ok"] and not r["errors"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
