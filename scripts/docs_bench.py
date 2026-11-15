"""Score the docs benchmark: answers written by a reader who saw only the built site.

    python3 scripts/docs_bench.py <answers_dir> [--json out.json]

<answers_dir> holds one file per task, <task id>.md, the reader's whole answer, and next to that folder readers.json:
per task, how sure the reader was that the answer works (`sure`, 1 to 5), the pages it had to re-read and what it
could not find. A task passes when every pattern of its `must` list (site/bench/tasks.json) is found in the answer
AND the reader was sure (4 or 5): a right-looking answer assembled from guesses is not a pass (the first run showed
keys alone pass 10 of 10 while three readers were guessing). No model judges anything. Prints the table and
"N of 10"; exits 0 (the bar, 9 of 10, is reported, not enforced here).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TASKS = json.loads((Path(__file__).resolve().parents[1] / "site" / "bench" / "tasks.json").read_text(encoding="utf-8"))["tasks"]


def score(answers: Path) -> list[dict]:
    rf = answers.parent / "readers.json"
    readers = json.loads(rf.read_text(encoding="utf-8")) if rf.is_file() else {}
    rows = []
    for t in TASKS:
        f = answers / f"{t['id']}.md"
        text = f.read_text(encoding="utf-8") if f.is_file() else ""
        missing = [p for p in t["must"] if not re.search(p, text, re.I)]
        r = readers.get(t["id"], {})
        sure = r.get("sure")
        rows.append({"id": t["id"], "answered": bool(text.strip()), "keys": bool(text.strip()) and not missing,
                     "sure": sure, "passed": bool(text.strip()) and not missing and (sure is None or sure >= 4),
                     "found": len(t["must"]) - len(missing), "of": len(t["must"]), "missing": missing,
                     "reread": r.get("reread", []), "not_found": r.get("missing", [])})
    return rows


def main() -> int:
    answers = Path(sys.argv[1])
    rows = score(answers)
    for r in rows:
        mark = "pass" if r["passed"] else ("FAIL" if r["answered"] else "no answer")
        sure = f"sure {r['sure']}/5" if r["sure"] is not None else "sure ?"
        print(f"{r['id']:<14} {mark:<9} keys {r['found']}/{r['of']}  {sure}  re-read {len(r['reread'])}  not found {len(r['not_found'])}"
              + (f"   missing keys: {r['missing']}" if r["missing"] and r["answered"] else ""))
    passed = sum(r["passed"] for r in rows)
    print(f"{passed} of {len(rows)} tasks pass (the bar is 9); keys alone: {sum(r['keys'] for r in rows)}; "
          f"pages re-read: {sum(len(r['reread']) for r in rows)}; things not found: {sum(len(r['not_found']) for r in rows)}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps({"passed": passed, "of": len(rows), "tasks": rows}, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
