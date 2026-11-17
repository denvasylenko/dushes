"""The form assistant alone (/agent/run, no site, no layer): does it refuse a page of the site that is not in its
form ("there is no car insurance in this application"), or hand the line back? The owner's three lines from the
loan application (insist_page_from_form). Agent only, code checks, a stop sum.
    FORMGUIDE_BASE=http://127.0.0.1:8095 uv run python scripts/form_alone_check.py --repeat 3 --max-usd 0.03 --label main"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harness_client import RUNS, Session  # noqa: E402

LINES = ["Okay, can you open car insurance", "Now, can you open car insurance tab", "Yeah, I said car insurance"]
REFUSED = re.compile(r"not available|isn't available|is not available|there is no car insurance|there.s no car insurance|no car insurance in this|"
                     r"doesn't offer|does not offer|not part of this|isn't part of this|can't open car insurance|cannot open car insurance", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--max-usd", type=float, required=True)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    out, spent = [], 0.0
    for i in range(a.repeat):
        if spent >= a.max_usd:
            print(f"stopped at ${spent:.4f}")
            break
        s = Session(f"form-alone-{i + 1}", "loan_application")
        for line in LINES:
            s.say(line)
        log = "\n".join(s.log)
        replies = [x[2:] for x in log.splitlines() if x.startswith("\U0001f916")]
        refused = [r for r in replies if REFUSED.search(r)]
        handed = "hand_back(" in log
        spent += 0.004   # a Session keeps no token counts: a run of three turns is priced at its usual cost, rounded up
        ok = handed and not refused
        out.append({"run": i + 1, "ok": ok, "handed_back": handed, "refused": refused, "log": log})
        print(f"{'pass' if ok else 'FAIL'} run {i + 1}: handed back {handed}; refused {len(refused)}  {refused[:1]}", flush=True)
    print(f"{sum(r['ok'] for r in out)}/{len(out)} pass; about ${spent:.3f} by the usual price of a run (a Session keeps no token counts)")
    path = RUNS / f"form-alone-{datetime.now():%Y%m%d-%H%M%S}{'-' + a.label if a.label else ''}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
