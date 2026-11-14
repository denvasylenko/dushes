"""The model benchmark's table: one row per agent model, from the scenario-eval reports of each model's run.

    # one run per agent model (the user and the judge stay on one model for all of them):
    uv run python scripts/evals.py --agent-model anthropic:claude-haiku-5-5 --repeat 3 --names-file evals/bench_set.txt
    uv run python scripts/evals.py --agent-model ollama:qwen3:8b --repeat 3 --names-file evals/bench_set.txt
    # the table from the reports:
    uv run python scripts/model_bench.py scripts/runs/evals-A.json scripts/runs/evals-B.json --out bench.md
        [--prices prices.json] [--hardware "Apple M1 Pro, 16 GB"] [--quant ollama:qwen3:8b=Q4_K_M]

Per model: the average and the held-out average, whether it passes the bar (held-out >= 8.5, none below 6), the
pass rate of the hard checks (the checks without a model), tool-call validity (tool errors per call, a change
card missing where one was expected), the median time to the first token and per turn, the cost per turn
(hosted: --prices, dollars per million tokens per model) or output tokens per second (local), and the most
frequent failure.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BAR_AVG, BAR_MIN = 8.5, 6.0


def _runs(r: dict) -> list[dict]:
    return r.get("runs") or [r]


def row(report: dict, prices: dict | None, quant: dict[str, str]) -> dict:
    model = report.get("agent_model") or "the demo server's model"
    res = report["scenarios"]
    held = [r["score"] for r in res if r["name"].startswith("heldout")]
    hard = [c for r in res for x in _runs(r) for c in x["checks"]]
    stats = [s for r in res for x in _runs(r) for s in x.get("runs_stats") or []]
    ttft = [s["ttft_ms"] for s in stats if s.get("ttft_ms") is not None]
    total = [s["total_ms"] for s in stats if s.get("total_ms") is not None]
    calls, errors = sum(s.get("tools") or 0 for s in stats), sum(s.get("tool_errors") or 0 for s in stats)
    card_checks = [c for c in hard if c["check"].startswith("shows a set_fields")]
    tok = Counter()
    for r in res:
        for x in _runs(r):
            for k, v in ((x.get("tokens") or {}).get("assistant") or {}).items():
                tok[k] += int(v or 0)
    cost = None
    if prices and model in prices and stats:
        p = prices[model]
        fresh = max(0, tok["input"] - tok["cache_read"])
        cost = (fresh * p["input"] + tok["cache_read"] * p.get("cache_read", p["input"]) + tok["output"] * p["output"]) / 1e6 / len(stats)
    out_ms = [(s["output_tokens"], s["model_ms"]) for s in stats if s.get("output_tokens") and s.get("model_ms")]
    tps = sum(o for o, _ in out_ms) / (sum(m for _, m in out_ms) / 1000) if out_ms else None
    failed = Counter(c["check"].split(" = ")[0] for c in hard if not c["ok"])
    reasons = Counter()
    for r in res:
        for x in r.get("lost") or []:
            reasons[x["reason"][:90]] += x["points"]
    typical = (failed.most_common(1)[0][0] if failed else "") or (reasons.most_common(1)[0][0] if reasons else "")
    avg_h = sum(held) / len(held) if held else None
    return {
        "commit": report.get("commit", ""), "user_model": report.get("user_model", ""), "judge_model": report.get("judge_model", ""),
        "repeat": report.get("repeat", 1),
        "model": model, "quant": quant.get(model, ""), "scenarios": len(res), "date": report["at"][:10],
        "average": round(report["average"], 2), "heldout": round(avg_h, 2) if avg_h is not None else None,
        "heldout_min": min(held) if held else None,
        "bar": bool(held) and avg_h >= BAR_AVG and min(held) >= BAR_MIN,
        "hard_pass": round(sum(c["ok"] for c in hard) / len(hard), 3) if hard else None,
        "tool_error_rate": round(errors / calls, 3) if calls else None,
        "card_missing": sum(not c["ok"] for c in card_checks), "card_expected": len(card_checks),
        "ttft_ms": round(statistics.median(ttft)) if ttft else None,
        "turn_ms": round(statistics.median(total)) if total else None,
        "cost_per_turn": round(cost, 5) if cost is not None else None, "tokens_per_s": round(tps, 1) if tps else None,
        "typical_failure": typical,
    }


def table(rows: list[dict], hardware: str) -> str:
    head = ("| model | avg | held-out (min) | bar | hard checks | tool errors | card missing | TTFT | turn | $/turn | tok/s | "
            "typical failure |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    lines = [f"Model benchmark, {date.today()}, {hardware}. The simulated user and the judge are the same for every row; "
             f"bar: held-out >= {BAR_AVG} and none below {BAR_MIN}.", "", head]
    for r in sorted(rows, key=lambda r: (-(r["heldout"] or 0), r["cost_per_turn"] or 0)):
        name = r["model"] + (f" ({r['quant']})" if r["quant"] else "")
        def f(v, fmt="{}"):
            return "–" if v is None else fmt.format(v)
        lines.append(f"| {name} | {r['average']} | {f(r['heldout'])} ({f(r['heldout_min'])}) | {'✅' if r['bar'] else '❌'} | "
                     f"{f(r['hard_pass'], '{:.0%}')} | {f(r['tool_error_rate'], '{:.1%}')} | {r['card_missing']}/{r['card_expected']} | "
                     f"{f(r['ttft_ms'], '{} ms')} | {f(r['turn_ms'], '{} ms')} | {f(r['cost_per_turn'], '${:.4f}')} | "
                     f"{f(r['tokens_per_s'])} | {r['typical_failure'][:70]} |")
    passing = [r for r in rows if r["bar"]]
    if passing:
        cheapest = min(passing, key=lambda r: (r["cost_per_turn"] if r["cost_per_turn"] is not None else 0, -(r["heldout"] or 0)))
        lines += ["", f"Cheapest model that passes the bar: **{cheapest['model']}**."]
    else:
        lines += ["", "No model passes the bar."]
    return "\n".join(lines) + "\n"


SITE = Path(__file__).resolve().parents[2] / "site" / "src" / "data" / "benchmarks" / "models.json"
LOCAL = ("ollama:", "lmstudio:", "vllm:", "local:")


def site_models(rows: list[dict], hardware: str, argv: list[str], target: Path = SITE) -> dict:
    """The docs' model comparison: one day and one commit per file (a mix is refused: not comparable)."""
    from bench import model_label
    days, commits = {r["date"] for r in rows}, {r["commit"] for r in rows}
    judges = {(r["user_model"], r["judge_model"]) for r in rows}
    if len(days) > 1 or len(commits) > 1 or len(judges) > 1:
        raise SystemExit(f"not comparable: days {sorted(days)}, commits {sorted(commits)}, user/judge {sorted(judges)}")
    models = []
    for r in rows:
        local = r["model"].startswith(LOCAL)
        models.append({"model": model_label(r["model"].split(":", 1)[-1]), "id": r["model"], "local": local, "quant": r["quant"],
                       "average": r["average"], "heldout": r["heldout"], "heldout_min": r["heldout_min"], "bar": r["bar"],
                       "hard_pass": r["hard_pass"], "tool_error_rate": r["tool_error_rate"], "card_missing": r["card_missing"],
                       "card_expected": r["card_expected"],
                       "ttft_s": round(r["ttft_ms"] / 1000, 1) if r["ttft_ms"] is not None else None,
                       "turn_s": round(r["turn_ms"] / 1000, 1) if r["turn_ms"] is not None else None,
                       "cost_per_turn_usd": None if local else r["cost_per_turn"], "tokens_per_s": r["tokens_per_s"] if local else None,
                       "typical_failure": r["typical_failure"]})
    passing = [m for m in models if m["bar"]]
    cheapest = min(passing, key=lambda m: (m["cost_per_turn_usd"] or 0, -(m["heldout"] or 0)))["id"] if passing else None
    first = rows[0]
    data = {"source": "backend/scripts/model_bench.py " + " ".join(argv), "date": first["date"], "commit": first["commit"],
            "user_model": model_label(first["user_model"]), "judge_model": model_label(first["judge_model"]),
            "hardware": hardware, "set": f"main + held-out ({first['scenarios']} scenarios)", "repeat": first["repeat"],
            "bar": {"heldout": BAR_AVG, "min": BAR_MIN}, "models": models, "cheapest_passing": cheapest}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"site numbers: {target}")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="The model benchmark's table from evals reports.")
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--prices", type=Path, help='{"<agent model>": {"input": .., "output": .., "cache_read": ..}} per 1M tokens')
    ap.add_argument("--hardware", default="", help="the machine the local models ran on")
    ap.add_argument("--quant", action="append", default=[], help="<agent model>=<quantisation>, for local models")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--site", action="store_true", help="write the docs' numbers: site/src/data/benchmarks/models.json")
    a = ap.parse_args()
    prices = json.loads(a.prices.read_text()) if a.prices else None
    quant = dict(q.split("=", 1) for q in a.quant)
    rows = [row(json.loads(p.read_text()), prices, quant) for p in a.reports]
    text = table(rows, a.hardware)
    print(text)
    if a.out:
        a.out.write_text(text)
        a.out.with_suffix(".json").write_text(json.dumps(rows, indent=2))
    if a.site:
        site_models(rows, a.hardware, sys.argv[1:])


if __name__ == "__main__":
    main()
