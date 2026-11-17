"""The local demo's turns for a day, from the files DEMO_RUNS_DIR holds (one JSON line a turn).

    python3 backend/scripts/demo_runs.py                 # today, the owner's turns
    python3 backend/scripts/demo_runs.py 2026-11-17 all  # a day, the team's test turns too
The folder: DEMO_RUNS_DIR, or backend/data/demo-runs of the main checkout.
"""
import datetime
import json
import os
import pathlib
import sys

day = next((a for a in sys.argv[1:] if a[:2] == "20"), datetime.date.today().isoformat())
everyone = "all" in sys.argv[1:]
folder = pathlib.Path(os.environ.get("DEMO_RUNS_DIR") or pathlib.Path.home() / "Documents/form_filler_claude/backend/data/demo-runs")
path = folder / f"{day}.jsonl"
rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
rows = [r for r in rows if everyone or r.get("by") == "owner"]
who = {"chooser": 0, "both": 0, "model": 0}
for r in rows:
    h = r.get("handled") or ""
    k = "both" if " then " in h else "chooser" if (r.get("chooser") or {}).get("handled") else "model"
    who[k] += 1
    done = "; ".join(str((s.get("value") or {}).get("path") or s.get("name")) for s in r.get("screen") or [])
    print(f"{r['time'][11:]}  {r.get('page') or '':12} {str(r.get('line') or '(' + r.get('kind', '') + ')')[:48]!r:52} "
          f"-> {done or 'nothing on the screen':22} | {(r.get('reply') or '')[:40]!r} | {h} | {r.get('seconds')} s")
print(f"\n{day}: {len(rows)} turns ({'everyone' if everyone else 'the owner'}); the chooser alone {who['chooser']}, "
      f"the chooser then the model {who['both']}, the model {who['model']}. File: {path}")
