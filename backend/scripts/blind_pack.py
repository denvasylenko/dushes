"""Packs conversations for blind scoring by another QA session: no model, commit or run name in any file.

    uv run python scripts/blind_pack.py scripts/runs/evals-A.json scripts/runs/evals-B.json --out <notes>/blind-dushes-2026-11-15
        [--only-differing] [--per-scenario 1] [--seed 7]

Each run of each report becomes conv-NN.md (shuffled; NN is its only label): the scenario's goal, what the guest
knows, what the site, its documents and the form say (the facts the scorer checks truth against; what the scenario
expects is left out, it would hand the scorer the answer), then the conversation as logged, without the checks and
without any score. rubric.md holds the rubric text and how to write scores.md
(label, score 0 to 10, one line on what cost points). The key (label -> report, scenario, run, agent model, whether
the code checks passed) is written to --key (default: scripts/runs/blind-key-<time>.json), never into the folder:
the author of the run keeps it and joins the scores afterwards with --join.

--only-differing: only scenarios whose code checks differ between the reports, plus --per-scenario random runs of
every other scenario (default 1), to keep a large comparison readable in a day.
--join scores.md --key key.json: prints the mean score per agent model and per scenario.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import evals  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
HOW = """# How to score

One file per conversation: conv-NN.md. Score each on its own, without looking at the others.
Write scores.md, one line per conversation:

    conv-07 | 6.5 | said the form shows no fee although the page gives 90 EUR

The score is 0 to 10 by the rubric below (version {version}). The facts in each file are the only source of truth
about the business; a fact found there is true. Do not guess which model or version wrote a conversation.

{rubric}
"""


def runs_of(report: dict, path: Path) -> list[dict]:
    out = []
    for s in report["scenarios"]:
        for i, r in enumerate(s.get("runs") or [s]):
            if r.get("transcript"):
                out.append({"report": str(path), "scenario": s["name"], "run": i + 1, "agent_model": report.get("agent_model"),
                            "commit": report.get("commit"), "passed_checks": all(c["ok"] for c in r.get("checks", [])),
                            "transcript": r["transcript"]})
    return out


def page_facts(sc) -> str:
    """Everything the assistants could have read: every page of the scenario's site (the site map's own text), the
    site's and the form's documents, and the form's own options, notes and computed values at the start. These are
    the facts a scorer checks truth against."""
    import yaml
    sys.path.insert(0, str(HERE))
    from demo.mock_forms import FORMS
    from demo.mock_forms.lab import site_map
    pages = (site_map() if sc.site == "/lab" else yaml.safe_load((HERE / "demo" / "site.yaml").read_text())).get("pages") or []
    if sc.site == "/lab":   # the Lab has a page per unrelated business: only the scenario's own page and the home page
        pages = [x for x in pages if x.get("path") in (sc.page, "/")]
    out = [evals.facts({x["path"]: x for x in pages}, sc)]
    form = FORMS.get(sc.form) if sc.form else None
    if form:
        cfg, lines = form.compute(sc.values or None), []
        for name, pr in (cfg.get("props") or {}).items():
            bits = [str(pr.get("label") or name)]
            if pr.get("options"):
                bits.append("options: " + ", ".join(str(o.get("name") or o.get("label") or o.get("id")) for o in pr["options"][:14]))
            for k in ("hint", "note", "description", "error"):
                if pr.get(k):
                    bits.append(f"{k}: {pr[k]}")
            v = (cfg.get("state") or {}).get(name)
            if v not in (None, "", [], {}, False):
                bits.append(f"value: {json.dumps(v, ensure_ascii=False)}")
            if len(bits) > 1:
                lines.append("- " + "; ".join(bits))
        notes = (form.domain or {}).get("glossary") or {}
        hints = (form.domain or {}).get("flow_hints") or []
        out.append(f"The form {sc.form} (what its fields offer and show at the start):\n" + "\n".join(lines[:80])
                   + ("\nThe form's notes: " + "; ".join(f"{k}: {v}" for k, v in notes.items()) if notes else "")
                   + ("\nThe form's rules of order: " + " ".join(hints) if hints else ""))
    return "\n\n".join(x for x in out if x.strip())[:14000]


def conversation(text: str) -> str:
    """The log without the checks, the score and the "who wrote each reply" list's model hints."""
    return text.split("\n\nCHECKS:")[0].rstrip()


def pick(items: list[dict], only_differing: bool, per: int, rnd: random.Random) -> list[dict]:
    if not only_differing:
        return items
    by: dict[str, list[dict]] = defaultdict(list)
    for x in items:
        by[x["scenario"]].append(x)
    out = []
    for xs in by.values():
        rate = defaultdict(list)
        for x in xs:
            rate[x["report"]].append(x["passed_checks"])
        differ = len({tuple(sorted(v)) for v in rate.values()}) > 1
        out += xs if differ else [y for rep in rate for y in rnd.sample([x for x in xs if x["report"] == rep], min(per, len(rate[rep])))]
    return out


def pack(reports: list[Path], out: Path, key: Path, only_differing: bool, per: int, seed: int) -> int:
    rnd = random.Random(seed)
    items = [x for p in reports for x in runs_of(json.loads(p.read_text()), p)]
    items = pick(items, only_differing, per, rnd)
    rnd.shuffle(items)
    scenarios = {s.name: s for s in evals.load_all()}
    out.mkdir(parents=True, exist_ok=True)
    keys = {}
    for n, x in enumerate(items, 1):
        label = f"conv-{n:02d}" if len(items) < 100 else f"conv-{n:03d}"
        path = HERE.parent / x["transcript"] if not Path(x["transcript"]).is_absolute() else Path(x["transcript"])
        if not path.exists():
            path = HERE / x["transcript"]
        sc = scenarios.get(x["scenario"])
        head = (f"# {label}\n\nGoal of the guest: {sc.goal}\nWhat the guest knows: {'; '.join(sc.knows)}\n"
                + (f"The true answer (from the documents): {sc.gold}\n" if sc.gold else "")
                + f"\n## What the site, its documents and the form say (true; anything about the business that is not here is unsupported)\n\n{page_facts(sc)}\n"
                ) if sc else f"# {label}\n"
        (out / f"{label}.md").write_text(head + "\n## Conversation\n\n" + conversation(path.read_text()) + "\n")
        keys[label] = {k: x[k] for k in ("report", "scenario", "run", "agent_model", "commit", "passed_checks")}
    (out / "rubric.md").write_text(HOW.format(version=evals.RUBRIC_VERSION, rubric=evals.RUBRIC))
    key.write_text(json.dumps(keys, indent=1))
    print(f"{len(items)} conversations in {out}\nkey (keep it, do not share): {key}")
    return 0


def join(scores: Path, key: Path) -> int:
    keys = json.loads(key.read_text())
    by_model, by_scenario = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for line in scores.read_text().splitlines():
        m = re.match(r"\s*(conv-\d+)\s*\|\s*([0-9.]+)\s*\|", line)
        if m and m.group(1) in keys:
            k = keys[m.group(1)]
            by_model[k["agent_model"]].append(float(m.group(2)))
            by_scenario[k["scenario"]][k["agent_model"]].append(float(m.group(2)))
    for model, v in sorted(by_model.items(), key=lambda kv: str(kv[0])):
        print(f"{model}: {sum(v) / len(v):.2f} over {len(v)} conversations")
    for name, d in sorted(by_scenario.items()):
        print(f"  {name}: " + ", ".join(f"{m} {sum(v) / len(v):.1f}" for m, v in sorted(d.items(), key=lambda kv: str(kv[0]))))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reports", nargs="*", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--key", type=Path)
    ap.add_argument("--only-differing", action="store_true")
    ap.add_argument("--per-scenario", type=int, default=1)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--join", type=Path, help="a scores.md to join with --key")
    a = ap.parse_args(argv)
    if a.join:
        return join(a.join, a.key)
    key = a.key or HERE / "scripts" / "runs" / f"blind-key-{datetime.now():%Y%m%d-%H%M%S}.json"
    return pack(a.reports, a.out, key, a.only_differing, a.per_scenario, a.seed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
