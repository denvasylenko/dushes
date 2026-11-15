"""Score the docs benchmark: answers written by a reader who saw only the built site.

    python3 scripts/docs_bench.py <answers_dir> [--json out.json]

<answers_dir> holds one file per task, <task id>.md, the reader's whole answer. A task passes when every pattern of
its `must` list (site/bench/tasks.json) is found in the answer. No model judges anything: the same answers always
give the same score. Prints the table and "N of 10"; exits 0 (the bar, 9 of 10, is reported, not enforced here).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TASKS = json.loads((Path(__file__).resolve().parents[1] / "site" / "bench" / "tasks.json").read_text(encoding="utf-8"))["tasks"]


def score(answers: Path) -> list[dict]:
    rows = []
    for t in TASKS:
        f = answers / f"{t['id']}.md"
        text = f.read_text(encoding="utf-8") if f.is_file() else ""
        missing = [p for p in t["must"] if not re.search(p, text, re.I)]
        rows.append({"id": t["id"], "answered": bool(text.strip()), "passed": bool(text.strip()) and not missing,
                     "found": len(t["must"]) - len(missing), "of": len(t["must"]), "missing": missing})
    return rows


def main() -> int:
    answers = Path(sys.argv[1])
    rows = score(answers)
    for r in rows:
        mark = "pass" if r["passed"] else ("FAIL" if r["answered"] else "no answer")
        print(f"{r['id']:<14} {mark:<9} {r['found']}/{r['of']}" + (f"   missing: {r['missing']}" if r["missing"] and r["answered"] else ""))
    passed = sum(r["passed"] for r in rows)
    print(f"{passed} of {len(rows)} tasks pass (the bar is 9)")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps({"passed": passed, "of": len(rows), "tasks": rows}, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
