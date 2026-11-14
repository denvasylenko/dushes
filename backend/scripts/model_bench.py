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


def _price(prices: dict | None, model: str) -> dict | None:
    """The model's price: from site/src/data/prices.json ({models: {id: ...}}) or a flat {model: price} file."""
    if not prices:
        return None
    from bench import price_for
    return price_for(prices, model, None) or prices.get(model)


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
    p = _price(prices, model)
    if p and stats:
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


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """The 95% Wilson interval of k passes in n runs."""
    if not n:
        return None
    ph, d = k / n, 1 + z * z / n
    c, h = (ph + z * z / (2 * n)) / d, z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def _pct(v: list[float], q: float) -> float | None:
    v = sorted(x for x in v if x is not None)
    return round(v[min(len(v) - 1, round(q * (len(v) - 1)))] / 1000, 2) if v else None


def sets_of(r: dict) -> list[str]:
    """The sets a scenario counts in: form, site, language, tools (a scenario may be in several), plus held-out."""
    tags, name = set(r.get("tags") or []), r["name"]
    out = []
    if "lang" in tags or r.get("lang") == "other":
        out.append("language")
    if any(c["check"].startswith(("calls ", "never calls ")) for x in _runs(r) for c in x.get("checks", [])):
        out.append("tools")
    if "navigation" in tags or any(c["check"].startswith(("reaches", "answered by dushes")) for x in _runs(r) for c in x.get("checks", [])):
        out.append("site")
    if not out or "lab" in tags:
        out.append("form")
    if name.startswith("heldout"):
        out.append("heldout")
    return out


def passed(run: dict, min_score: float) -> bool:
    """A run passes: every code check holds and the judge's score reaches the scenario's own floor."""
    return all(c["ok"] for c in run.get("checks", [])) and run.get("score", 0) >= min_score


def _loss(r: dict, run: dict, root: Path) -> dict:
    """One lost run for the page: the scenario, the first user message, the reply after it, what was found."""
    user = reply = ""
    path = root / str(run.get("transcript") or "")
    if run.get("transcript") and path.exists():
        lines = path.read_text().split("\n")
        i = next((k for k, x in enumerate(lines) if x.startswith("\U0001f464 ")), None)
        if i is not None:
            user = lines[i][2:].strip()
            reply = next((x[2:].strip() for x in lines[i + 1:] if x.startswith("\U0001f916 ")), "")
    failed = [c["check"] for c in run.get("checks", []) if not c["ok"]]
    why = max(run.get("lost") or [{"points": 0, "reason": ""}], key=lambda x: x["points"])["reason"]
    return {"scenario": r["name"], "path": f"backend/evals/{r.get('file') or r['name'] + '.yaml'}", "score": run.get("score"),
            "user": user[:240], "reply": reply[:400], "failed_checks": failed[:4], "judge": " ".join(str(why).split())[:300]}


def model_detail(report: dict, prices: dict | None, root: Path) -> dict:
    res = report["scenarios"]
    model = report.get("agent_model") or "anthropic:claude-haiku-5-5"
    by: dict[str, dict] = {}
    for r in res:
        runs = _runs(r)
        for name in sets_of(r):
            b = by.setdefault(name, {"scenarios": 0, "runs": 0, "passes": 0, "scores": []})
            b["scenarios"] += 1
            b["runs"] += len(runs)
            b["passes"] += sum(passed(x, r["min_score"]) for x in runs)
            b["scores"] += [x["judge_score"] for x in runs if x.get("judge_score") is not None]
    sets = {k: {"scenarios": b["scenarios"], "repeat": round(b["runs"] / b["scenarios"]) if b["scenarios"] else 0, "runs": b["runs"],
                "passes": b["passes"], "pass_rate": round(b["passes"] / b["runs"], 3) if b["runs"] else None,
                "interval95": wilson(b["passes"], b["runs"]),
                "judge_mean": round(statistics.mean(b["scores"]), 2) if b["scores"] else None,
                "judge_sd": round(statistics.pstdev(b["scores"]), 2) if len(b["scores"]) > 1 else None} for k, b in sorted(by.items())}
    all_runs = [(r, x) for r in res for x in _runs(r)]
    stats = [st for _r, x in all_runs for st in x.get("runs_stats") or []]
    ttft, turn = [st.get("ttft_ms") for st in stats], [st.get("total_ms") for st in stats]
    costs = []
    price = _price(prices, model)
    if price:
        for _r, x in all_runs:
            t, n = (x.get("tokens") or {}).get("assistant") or {}, max(1, len(x.get("runs_stats") or []))
            fresh = max(0, (t.get("input") or 0) - (t.get("cache_read") or 0))
            costs.append((fresh * price["input"] + (t.get("cache_read") or 0) * price.get("cache_read", price["input"])
                          + (t.get("output") or 0) * price["output"]) / 1e6 / n)
    cost = round(statistics.median(costs), 5) if costs and any(costs) else None
    k, n = sum(passed(x, r["min_score"]) for r, x in all_runs), len(all_runs)
    rate = round(k / n, 3) if n else None
    lost = sorted(((r, x) for r, x in all_runs if not passed(x, r["min_score"])), key=lambda p: p[1].get("score", 0))
    seen, losses = set(), []
    for r, x in lost:
        if r["name"] not in seen:
            seen.add(r["name"])
            losses.append(_loss(r, x, root))
        if len(losses) == 5:
            break
    code_fail = sum(1 for _r, x in all_runs for c in x.get("checks", []) if not c["ok"])
    return {"id": model, "local": model.startswith(LOCAL), "scenarios": len(res), "repeat": report.get("repeat", 1), "runs": n,
            "passes": k, "pass_rate": rate, "interval95": wilson(k, n), "code_check_failures": code_fail, "sets": sets,
            "ttft_p50_s": _pct(ttft, 0.5), "ttft_p95_s": _pct(ttft, 0.95), "turn_p50_s": _pct(turn, 0.5), "turn_p95_s": _pct(turn, 0.95),
            "turns": len(stats), "cost_per_turn_usd": cost,
            "quality_per_dollar": round(rate / cost) if rate is not None and cost else None,   # pass rate / cost per turn
            "losses": losses, "report": report.get("_path", "")}


def second_judge(files: list[Path]) -> dict | None:
    """rejudge.py reports, one per model: the other judge's means and how often the two judges agree within a point."""
    if not files:
        return None
    out: dict = {"model": None, "sample": 0, "agreement": None, "means": {}}
    agree = total = 0
    for f in files:
        d = json.loads(f.read_text())
        out["model"] = d["second_judge"]
        out["sample"] += d["n"]
        agree += sum(abs(x["diff"]) <= 1 for x in d["rows"])
        total += d["n"]
        src = json.loads(Path(d["report"]).read_text()) if Path(d["report"]).exists() else {}
        out["means"][src.get("agent_model") or d["report"]] = {"first": d["mean_first"], "second": d["mean_second"]}
    out["agreement"] = round(agree / total, 3) if total else None   # the share of conversations scored within 1 point
    return out


def site_models(reports: list[dict], prices: dict | None, hardware: str, argv: list[str], rejudges: list[Path] | None = None,
                target: Path = SITE) -> dict:
    """The docs' model comparison, nothing typed: one day, one commit, one user and one judge per file (a mix is
    refused: not comparable)."""
    key = {(r["at"][:10], r.get("commit", ""), r.get("user_model", ""), r.get("judge_model", "")) for r in reports}
    if len(key) > 1:
        raise SystemExit(f"not comparable: (day, commit, user, judge) differ: {sorted(key)}")
    root = Path(__file__).resolve().parents[1]
    models = [model_detail(r, prices, root) for r in reports]
    first = reports[0]
    total = None
    if prices:
        from eval_summary import cost as tokens_cost
        total = 0.0
        for r in reports:   # the agent at its own price is in cost_per_turn; the user and the judge at theirs
            tok, _ = tokens_cost(r["scenarios"], {"input": 0, "output": 0, "cache_read": 0})
            for who, mid in (("assistant", r.get("agent_model") or "claude-haiku-5-5"), ("user_and_judge", r.get("judge_model") or "")):
                pr, t = _price(prices, mid), tok.get(who) or {}
                if pr:
                    total += (max(0, t.get("input", 0) - t.get("cache_read", 0)) * pr["input"] + t.get("cache_read", 0) * pr.get("cache_read", pr["input"])
                              + t.get("output", 0) * pr["output"]) / 1e6
        total = round(total, 2)
    data = {"date": first["at"][:10], "commit": first.get("commit", ""), "hardware": hardware,
            "bar": {"heldout": BAR_AVG, "min": BAR_MIN},
            "method": {"code_checked": "says, never_says, cards, fields, tools and the other expect keys: counted from the events; a failed check fails the run",
                       "judged": "truth, the right agent, cards instead of prose, the goal, brevity: a fixed rubric, 0 to 10 (backend/evals/README.md)",
                       "pass": "a run passes when every code check holds and the judge's score reaches the scenario's min_score",
                       "judge_model": first.get("judge_model", ""), "judge_why": "a fixed model stronger than the agents, the same for every row",
                       "user_model": first.get("user_model", ""), "prices_checked": (prices or {}).get("checked"),
                       "prices_source": (prices or {}).get("source"), "quality_per_dollar": "pass rate / median cost per turn in dollars"},
            "total_cost_usd": total, "models": models, "second_judge": second_judge(rejudges or []),
            "reproduce": "bash backend/scripts/model_compare.sh", "source": "backend/scripts/model_bench.py " + " ".join(argv)}
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
    ap.add_argument("--rejudge", action="append", default=[], type=Path, help="a rejudge.py report (one per model): the second judge")
    a = ap.parse_args()
    prices = json.loads(a.prices.read_text()) if a.prices else None
    quant = dict(q.split("=", 1) for q in a.quant)
    reports = [{**json.loads(p.read_text()), "_path": f"backend/scripts/runs/{p.name}"} for p in a.reports]
    rows = [row(r, prices, quant) for r in reports]
    text = table(rows, a.hardware)
    print(text)
    if a.out:
        a.out.write_text(text)
        a.out.with_suffix(".json").write_text(json.dumps(rows, indent=2))
        # the internal report's detail (sets, intervals, losses, the second judge): next to the table, not under site/
        site_models(reports, prices, a.hardware, sys.argv[1:], a.rejudge, a.out.with_suffix(".detail.json"))
    if a.site:
        site_models(reports, prices, a.hardware, sys.argv[1:], a.rejudge)


if __name__ == "__main__":
    main()
