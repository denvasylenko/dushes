"""A round summary of the scenario evals: the average (overall and by tag), the worst scenarios, the failed checks
that recur, the judge's reasons and what the run cost.

    uv run python scripts/eval_summary.py                          # the latest report in scripts/runs/
    uv run python scripts/eval_summary.py scripts/runs/evals-<time>.json --prev scripts/runs/evals-<earlier>.json
    uv run python scripts/eval_summary.py --prices '{"input": 0.10, "output": 0.50, "cache_read": 0.01}'

Prices are dollars per million tokens (default: Claude Haiku 5.5, the demo's models). `input` counts every input
token; the cache_read part of it is priced at `cache_read`.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

RUNS = Path(__file__).parent / "runs"
HAIKU = {"input": 0.10, "output": 0.50, "cache_read": 0.01}
KINDS = ("fill", "fix", "mind", "voice", "lang", "dump", "inject", "offtopic", "rule", "facts")


def _runs(r: dict) -> list[dict]:
    return r.get("runs") or [r]


def cost(results: list[dict], prices: dict) -> tuple[dict, float]:
    tok: dict[str, dict[str, int]] = {"assistant": Counter(), "user_and_judge": Counter()}
    for r in results:
        for x in _runs(r):
            for who, t in (x.get("tokens") or {}).items():
                for k, v in (t or {}).items():
                    tok.setdefault(who, Counter())[k] += int(v or 0)
    usd = 0.0
    for t in tok.values():
        fresh = max(0, t["input"] - t["cache_read"])
        usd += (fresh * prices["input"] + t["cache_read"] * prices["cache_read"] + t["output"] * prices["output"]) / 1e6
    return {k: dict(v) for k, v in tok.items()}, round(usd, 4)


def _lang(r: dict) -> str:
    """The report's language of a scenario (older reports: from the tags and the name)."""
    if r.get("lang"):
        return r["lang"]
    return "other" if "lang" in (r.get("tags") or []) or "language" in r["name"] or r["name"].startswith("russian_") else "en"


def tag_of(r: dict) -> list[str]:
    tags = set(r.get("tags") or [])
    name = r["name"]
    if name.startswith("heldout"):
        tags.add("heldout")
    if name.startswith(("lab_", "heldout_lab_")):
        tags.add("lab")
        tags.update(k for k in KINDS if name.endswith("_" + k) or f"_{k}_" in name)
    return sorted(tags) or ["main"]


def summary(report: dict, prev: dict | None, prices: dict, worst: int = 10) -> str:
    res = report["scenarios"]
    before = {r["name"]: r["score"] for r in (prev or {}).get("scenarios", [])}
    avg = report["average"]
    out = [f"# Eval round {report['at']} ({'offline' if report.get('offline') else 'live'})", "",
           f"Scenarios: {len(res)}. Average: **{avg}**"
           + (f" (previous {prev['average']}, {avg - prev['average']:+.2f})" if prev else "")
           + f". Below min_score: {sum(r['score'] < r['min_score'] for r in res)}.", ""]
    by: dict[str, list[float]] = defaultdict(list)
    for r in res:
        for t in tag_of(r):
            by[t].append(r["score"])
    held = [r["score"] for r in res if "heldout" in tag_of(r)]
    rest = [r["score"] for r in res if "heldout" not in tag_of(r)]
    if held and rest:   # a gap between the two is the sign of prompts tuned to the tests
        out += [f"Held-out: **{sum(held) / len(held):.2f}** ({len(held)}) vs tuned-on: {sum(rest) / len(rest):.2f} ({len(rest)}).", ""]
    en = [r["score"] for r in res if _lang(r) == "en"]
    other = [r["score"] for r in res if _lang(r) == "other"]
    if en and other:   # customers write mostly in English: its own row next to the whole
        out += [f"In English: **{sum(en) / len(en):.2f}** ({len(en)}); other languages and switches: "
                f"{sum(other) / len(other):.2f} ({len(other)}).", ""]
    if held:   # the "done" bar: held-out average >= 8.5 and no held-out scenario below 6
        ok = sum(held) / len(held) >= 8.5 and min(held) >= 6
        out += [f"Target (held-out average >= 8.5, none below 6; lowest {min(held)}): **{'MET' if ok else 'not met'}**.", ""]
    out += ["| tag | n | average |", "|---|---|---|"]
    out += [f"| {t} | {len(v)} | {sum(v) / len(v):.2f} |" for t, v in sorted(by.items())]
    out += ["", f"## The {worst} worst", ""]
    for r in sorted(res, key=lambda r: r["score"])[:worst]:
        failed = [c["check"] for c in r["checks"] if not c["ok"]]
        reason = max(r.get("lost") or [{"points": 0, "reason": ""}], key=lambda x: x["points"])["reason"]
        delta = f" (was {before[r['name']]})" if r["name"] in before else ""
        out.append(f"- **{r['name']}** {r['score']}{delta}: failed {failed or 'none'}; judge: {reason[:220]}")
    checks = Counter(re.sub(r" = .*| a \w+ card|\s.*", lambda m: m.group(0) if m.group(0).startswith(" a ") else "", c["check"])
                     for r in res for c in r["checks"] if not c["ok"])
    out += ["", "## Failed checks that recur", ""] + [f"- {k}: {v}" for k, v in checks.most_common(12)]
    lost = sorted(((x["points"], r["name"], x["reason"]) for r in res for x in r.get("lost") or []), reverse=True)
    out += ["", "## The judge's biggest deductions", ""] + [f"- -{p} {n}: {why[:240]}" for p, n, why in lost[:25]]
    tok, usd = cost(res, prices)
    out += ["", "## Cost", "", f"Tokens: {json.dumps(tok)}", f"Estimated cost: **${usd}** at {json.dumps(prices)} per 1M tokens."]
    return "\n".join(out) + "\n"


SITE = Path(__file__).resolve().parents[2] / "site" / "src" / "data" / "benchmarks" / "evals.json"


def _line(text: str, n: int = 140) -> str:
    """One short line: the first sentence, cut at a word."""
    t = " ".join(str(text).split())
    t = re.split(r"(?<=[.;])\s", t, maxsplit=1)[0]
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "\u2026"


def _avg(v: list[float]) -> dict:
    return {"average": round(sum(v) / len(v), 2) if v else None, "count": len(v)}


def site_evals(report: dict, path: Path, prices: dict, target: Path = SITE) -> dict:
    """The docs' Benchmarks page numbers for the scenario evals (one round)."""
    from bench import model_label
    res = report["scenarios"]
    held = [r["score"] for r in res if "heldout" in tag_of(r)]
    by: dict[str, list[float]] = defaultdict(list)
    for r in res:
        for t in tag_of(r):
            by[t].append(r["score"])
    worst = []
    for r in sorted(res, key=lambda r: r["score"])[:10]:
        lost = max(r.get("lost") or [{"points": 0, "reason": ""}], key=lambda x: x["points"])["reason"]
        failed = [c["check"] for c in r["checks"] if not c["ok"]]
        worst.append({"name": r["name"], "score": r["score"], "reason": _line(lost or (f"failed: {failed[0]}" if failed else ""))})
    _tok, usd = cost(res, prices)
    d0, d1 = str(report.get("started") or report["at"])[:10], report["at"][:10]
    data = {"source": "backend/scripts/evals.py" + (f" --agent-model {report['agent_model']}" if report.get("agent_model") else ""),
            **({"date": d1} if d0 == d1 else {"date_from": d0, "date_to": d1}),
            "commit": report.get("commit", ""), "agent_model": model_label((report.get("agent_model") or "claude-haiku-5-5").split(":", 1)[-1]),
            "user_model": model_label(report.get("user_model") or ""), "judge_model": model_label(report.get("judge_model") or ""),
            "scenarios": len(res), "repeat": report.get("repeat", 1), "average": report["average"],
            "heldout": {"average": round(sum(held) / len(held), 2) if held else None, "min": min(held) if held else None,
                        "count": len(held)},
            "english": _avg([r["score"] for r in res if _lang(r) == "en"]),
            "other_languages": _avg([r["score"] for r in res if _lang(r) == "other"]),
            "heldout_english": _avg([r["score"] for r in res if _lang(r) == "en" and "heldout" in tag_of(r)]),
            "target": {"average": 8.5, "min": 6, "met": bool(held) and sum(held) / len(held) >= 8.5 and min(held) >= 6},
            "by_tag": {t: {"n": len(v), "average": round(sum(v) / len(v), 2)} for t, v in sorted(by.items())},
            "worst": worst, "cost_usd": usd, "report": str(path.resolve().relative_to(Path(__file__).resolve().parents[2]))}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"site numbers: {target}")
    return data


def latest_live() -> Path:
    """The newest live report (offline runs, the tests' included, are skipped)."""
    for p in sorted(RUNS.glob("evals-*.json"), reverse=True):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        if not d.get("offline") and len(d.get("scenarios") or []) > 1:
            return p
    raise SystemExit("no live evals report in scripts/runs/")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report", nargs="?", type=Path)
    ap.add_argument("--prev", type=Path)
    ap.add_argument("--prices", default=json.dumps(HAIKU))
    ap.add_argument("--out", type=Path, help="write the Markdown here as well")
    ap.add_argument("--site", action="store_true", help="write the docs' numbers: site/src/data/benchmarks/evals.json")
    a = ap.parse_args()
    path = a.report or latest_live()
    text = summary(json.loads(path.read_text()), json.loads(a.prev.read_text()) if a.prev else None, json.loads(a.prices))
    print(text)
    if a.out:
        a.out.write_text(text)
    if a.site:
        site_evals(json.loads(path.read_text()), path, json.loads(a.prices))


if __name__ == "__main__":
    main()
