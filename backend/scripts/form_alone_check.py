"""The form assistant alone (/agent/run, no site, no layer), the owner's lines from the loan application. Agent
only, code checks, a stop sum; the spend is the runs' own cost_usd (run_stats).
  --case insurance: does it refuse a page of the site that is not in its form ("there is no car insurance in this
    application"), or hand the line back? (insist_page_from_form)
  --case open_all: "Open all sections" with the Applicant tab on the screen and every section folded: the first reply
    opens all five sections and never says it cannot (open_all_sections_agent)
    FORMGUIDE_BASE=http://127.0.0.1:8095 uv run python scripts/form_alone_check.py --case open_all --repeat 3 --max-usd 0.03"""
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
OPEN_ALL = ["Open all sections", "Yeah, but like all sections", "Yeah, but like I told you, in applicant, open all sections"]
APPLICANT = ["acc_personal", "acc_passport", "acc_addresses", "acc_contacts", "acc_education"]
CANNOT = re.compile(r"can't open|cannot open|can not open|unable to open|one at a time|only one section|only open one|can't expand|cannot expand", re.I)
REFUSED = re.compile(r"not available|isn't available|is not available|there is no car insurance|there.s no car insurance|no car insurance in this|"
                     r"doesn't offer|does not offer|not part of this|isn't part of this|can't open car insurance|cannot open car insurance", re.I)


def io_cost(io: list[int]) -> float:
    """Haiku 5.5 list price, no cache read: 0.10 USD a million input tokens, 0.50 a million output."""
    return io[0] * 0.10 / 1e6 + io[1] * 0.50 / 1e6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--max-usd", type=float, required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--case", choices=["insurance", "open_all"], default="insurance")
    a = ap.parse_args()
    out, spent, io = [], 0.0, [0, 0]
    for i in range(a.repeat):
        if spent >= a.max_usd:
            print(f"stopped at ${spent:.4f}")
            break
        s = Session(f"form-alone-{i + 1}", "loan_application")
        if a.case == "open_all":
            s.say(OPEN_ALL[0])
            first = "\n".join(s.log)
            for line in OPEN_ALL[1:]:
                s.say(line)
            log = "\n".join(s.log)
            moves = [x for x in first.splitlines() if x.strip().startswith(("\U0001f526", "\u2699"))]
            missing = [n for n in APPLICANT if not any(re.search(rf"\b{n}\b", m) for m in moves)]
            first_replies = [x[2:] for x in first.splitlines() if x.startswith("\U0001f916")]
            cannot = [r for r in (x[2:] for x in log.splitlines() if x.startswith("\U0001f916")) if CANNOT.search(r)]
            ok = not missing and not cannot
            out.append({"run": i + 1, "ok": ok, "missing_on_first": missing, "cannot": cannot, "first_reply": first_replies[:1], "log": log})
            print(f"{'pass' if ok else 'FAIL'} run {i + 1}: first line left closed {missing}; 'cannot' {len(cannot)}  {cannot[:1]}", flush=True)
        else:
            for line in LINES:
                s.say(line)
            log = "\n".join(s.log)
            replies = [x[2:] for x in log.splitlines() if x.startswith("\U0001f916")]
            refused = [r for r in replies if REFUSED.search(r)]
            handed = "hand_back(" in log
            ok = handed and not refused
            out.append({"run": i + 1, "ok": ok, "handed_back": handed, "refused": refused, "log": log})
            print(f"{'pass' if ok else 'FAIL'} run {i + 1}: handed back {handed}; refused {len(refused)}  {refused[:1]}", flush=True)
        spent += s.cost_usd
        io = [io[0] + s.tokens_io[0], io[1] + s.tokens_io[1]]
        if not s.cost_usd:   # /agent/run sends no cost: the stop counts the tokens at Haiku's list price, no cache
            spent += io_cost(s.tokens_io)
    print(f"{sum(r['ok'] for r in out)}/{len(out)} pass; tokens {io[0]} in / {io[1]} out; "
          f"${spent:.4f} (cost_usd where the route sends it, else the tokens at the list price with no cache: an upper estimate)")
    path = RUNS / f"form-alone-{a.case}-{datetime.now():%Y%m%d-%H%M%S}{'-' + a.label if a.label else ''}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
