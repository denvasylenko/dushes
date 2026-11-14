"""Every honest live run, one row each, for the docs' Benchmarks page (site/src/data/benchmarks/history.json).

    uv run python scripts/bench_history.py            # print the table
    uv run python scripts/bench_history.py --site     # and write history.json

Reads scripts/runs/evals-*.json (scenario evals), recipes-*.json, load-*.json, landing-*.json and scripts/bench-*.json
(speed). Offline runs are skipped; a run in which no scenario ran (a server that was down) is listed as broken and
left out of the file. A row: {date, time, kind, models: {agent, user, judge}, scenarios, repeat, average, heldout,
report, comparable, note}. `comparable` groups runs measured with the same judge (scores from different judges are
not compared); runs from before the judge was recorded say so in `note`.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUNS = HERE / "scripts" / "runs"
TARGET = HERE.parent / "site" / "src" / "data" / "benchmarks" / "history.json"

# Runs whose numbers measure a fault of the test, not of the product: left out, with the reason, never hidden.
EXCLUDE = {
    "recipes-20261114-163438.json": "the prefill and confirm fixtures were wrong (a locked step, a Sunday); rerun later",
    "recipes-20261114-171027.json": "the confirm runner missed a held tool's result (fixed in the runner)",
    "recipes-20261114-171816.json": "the confirm runner missed a held tool's result (fixed in the runner)",
    "evals-20261114-203120.json": "another host's pilot (Herefront's cabinet) on a harness that did not yet know its form routes",
}


def _id(m: str | None) -> str:
    return (m or "").split(":", 1)[-1]


def _when(at: str) -> tuple[str, str]:
    return at[:10], at[11:16]


def evals_rows() -> tuple[list[dict], list[str]]:
    rows, broken = [], []
    for f in sorted(glob.glob(str(RUNS / "evals-*.json"))):
        d = json.loads(Path(f).read_text())
        res = d.get("scenarios") or []
        if d.get("offline") or len(res) < 2:
            continue
        ran = [r for r in res if not any(c.get("check") in ("the scenario ran", "no run errors") and not c.get("ok") for c in r.get("checks", []))]
        if Path(f).name in EXCLUDE:
            broken.append(f"{Path(f).name}: {EXCLUDE[Path(f).name]}")
            continue
        if len(ran) < len(res) / 2:
            broken.append(f"{Path(f).name}: {len(res) - len(ran)} of {len(res)} scenarios did not run (the server was down)")
            continue
        agent = _id(d.get("agent_model")) or "claude-haiku-5-5"
        judge = _id(d.get("judge_model") or d.get("model")) or agent   # before --model/--judge-model the agent's model judged
        user = _id(d.get("user_model") or d.get("model")) or agent
        held = [r["score"] for r in res if r["name"].startswith("heldout")]
        n = len(res)
        kind = "full round" if n >= 150 else "model comparison" if agent != "claude-haiku-5-5" else "scenario set"
        date, time = _when(d["at"])
        rows.append({"date": date, "time": time, "kind": kind, "models": {"agent": agent, "user": user, "judge": judge},
                     "scenarios": n, "repeat": d.get("repeat", 1), "average": d["average"],
                     "heldout": round(sum(held) / len(held), 2) if held else None,
                     "report": f"backend/scripts/runs/{Path(f).name}", "comparable": f"judge {judge}",
                     "note": "" if d.get("judge_model") or d.get("model") else "the judge was the agent's own model"})
    return rows, broken


def recipes_rows() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(RUNS / "recipes-*.json"))):
        if f.endswith("-offline.json"):
            continue
        d = json.loads(Path(f).read_text())
        if d.get("offline"):
            continue
        if Path(f).name in EXCLUDE:
            continue   # listed in left_out by main()
        sc = d.get("scenarios") or []
        runs, hits = sum(s["runs"] for s in sc), sum(s["hits"] for s in sc)
        date, time = _when(d["at"])
        rows.append({"date": date, "time": time, "kind": "recipes", "models": {"agent": sc[0]["model"] if sc else "", "user": "scripted", "judge": "none"},
                     "scenarios": len(sc), "repeat": max((s["runs"] for s in sc), default=0), "average": round(hits / runs * 10, 2) if runs else None,
                     "heldout": None, "report": f"backend/scripts/runs/{Path(f).name}", "comparable": "tool calls",
                     "note": f"{hits} of {runs} runs called the expected tool (average = hits per 10 runs)"})
    return rows


def speed_rows() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(HERE / "scripts" / "bench-*.json"))):
        d = json.loads(Path(f).read_text())
        sc = [s for s in d.get("scenarios") or [] if s.get("ttft_median_ms") is not None]
        if not sc:
            continue
        name = Path(f).stem.split("-", 1)[1]
        date = f"{name[:4]}-{name[4:6]}-{name[6:8]}"
        rows.append({"date": date, "time": f"{name[9:11]}:{name[11:13]}", "kind": "speed", "models": {"agent": "claude-haiku-5-5", "user": "scripted", "judge": "none"},
                     "scenarios": len(sc), "repeat": d.get("repeat", 1), "average": None, "heldout": None,
                     "report": f"backend/scripts/{Path(f).name}", "comparable": "speed",
                     "note": "median first word " + ", ".join(f"{s['scenario']} {s['ttft_median_ms'] / 1000:.1f}s" for s in sc)})
    return rows


def load_rows() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(RUNS / "load-*.json"))):
        d = json.loads(Path(f).read_text())
        st = d.get("steps") or []
        if not st:
            continue
        date, time = _when(d["at"])
        rows.append({"date": date, "time": time, "kind": "load", "models": {"agent": "claude-haiku-5-5", "user": "scripted", "judge": "none"},
                     "scenarios": len(st), "repeat": d.get("turns", 1), "average": None, "heldout": None,
                     "report": f"backend/scripts/runs/{Path(f).name}", "comparable": "load",
                     "note": "p95 first word " + ", ".join(f"{s['visitors']} visitors {s['ttft_p95_s']}s" for s in st)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", action="store_true", help="write site/src/data/benchmarks/history.json")
    a = ap.parse_args()
    ev, broken = evals_rows()
    broken += [f"{k}: {v}" for k, v in EXCLUDE.items() if k.startswith("recipes-") and (RUNS / k).exists()]
    rows = sorted(ev + recipes_rows() + speed_rows() + load_rows(), key=lambda r: (r["date"], r["time"]))
    for r in rows:
        print(f"{r['date']} {r['time']} {r['kind']:<16} n={r['scenarios']:<4} x{r['repeat']} avg {r['average']} held {r['heldout']} "
              f"judge {r['models']['judge']} {r['note'][:60]}")
    for b in broken:
        print("broken, left out:", b)
    if a.site:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(json.dumps({"runs": rows, "left_out": broken}, indent=1) + "\n")
        print(f"site numbers: {TARGET}")


if __name__ == "__main__":
    main()
