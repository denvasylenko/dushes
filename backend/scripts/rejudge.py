"""A second opinion on a round: the same conversations scored again by another judge model, to see whether the
first judge leans one way (e.g. a Claude judge on a Claude agent).

    uv run python scripts/rejudge.py scripts/runs/evals-<time>.json --judge openai:<model> --sample 30

Takes a finished evals report, picks a sample of its scenarios (every k-th by name, so it is the same sample each
time), reads each conversation's transcript (scripts/runs/eval-<name>.txt, as the report names it) and asks the other
judge with the same rubric and the same facts-free prompt. Deterministic checks are not rerun: only the judge's own
score is compared (`judge_score`, before any cap). Writes scripts/runs/rejudge-<time>.json:
{first_judge, second_judge, n, mean_first, mean_second, mean_diff, max_abs_diff, rows: [{name, first, second, diff}]}.
A transcript from a later run of the same scenario would not match its score, so run this right after the round.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import evals  # noqa: E402

HERE = Path(__file__).resolve().parents[1]


def sample(results: list[dict], n: int) -> list[dict]:
    ok = sorted((r for r in results if r.get("transcript") and r.get("judge_score") is not None), key=lambda r: r["name"])
    step = max(1, len(ok) // max(1, n))
    return ok[::step][:n]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report", type=Path)
    ap.add_argument("--judge", required=True, help="the second judge, e.g. openai:<model>")
    ap.add_argument("--sample", type=int, default=30)
    a = ap.parse_args(argv)
    from formguide.models import build_model
    report = json.loads(a.report.read_text())
    second = build_model(a.judge)
    scenarios = {s.name: s for s in evals.load_all()}
    rows = []
    for r in sample(report["scenarios"], a.sample):
        run = (r.get("runs") or [r])[0]   # with --repeat: the first run's own score and transcript
        path = HERE / str(run.get("transcript") or r["transcript"])
        sc = scenarios.get(r["name"])
        if not path.exists() or sc is None:
            continue
        v = evals.judge(second, sc, path.read_text().split("\n\nCHECKS:")[0])
        first = float(run.get("judge_score") if run.get("judge_score") is not None else r["judge_score"])
        rows.append({"name": r["name"], "first": first, "second": v.score, "diff": round(v.score - first, 2)})
        print(f"{r['name']:<44} {first:>4} -> {v.score:>4}", flush=True)
    if not rows:
        print("no transcripts to rejudge")
        return 1
    mean = lambda k: round(sum(x[k] for x in rows) / len(rows), 2)  # noqa: E731
    out = {"at": datetime.now().isoformat(timespec="seconds"), "report": str(a.report), "first_judge": report.get("judge_model") or report.get("model"),
           "second_judge": a.judge, "n": len(rows), "mean_first": mean("first"), "mean_second": mean("second"), "mean_diff": mean("diff"),
           "max_abs_diff": max(abs(x["diff"]) for x in rows), "rows": rows}
    target = HERE / "scripts" / "runs" / f"rejudge-{datetime.now():%Y%m%d-%H%M%S}.json"
    target.write_text(json.dumps(out, indent=1))
    print(f"first {out['mean_first']}, second {out['mean_second']}, mean diff {out['mean_diff']}, max |diff| {out['max_abs_diff']}\nreport: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
