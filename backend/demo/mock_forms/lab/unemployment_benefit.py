"""Lab form: an unemployment benefit application at the Norland Employment Service (medium, repeating group).

Rules: the employment history is a repeating group of 1 to 5 jobs (employer, from, to); each job's "to" date is
after its "from" date and not in the future; the reason for leaving the last job is a dropdown, and "resigned" shows
the read-only notice "the benefit may be delayed by 12 weeks" (computed; hidden for other reasons); "other" asks for
details; the last working day is not in the future; the termination letter upload is required; the bank IBAN is
validated; the availability-for-work checkbox is required; national id numbers have 11 digits.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "unemployment_benefit"
SEQUENTIAL = False
MAX_JOBS = 5
RESIGN_NOTICE = ("You resigned: the benefit may be delayed by 12 weeks from your last working day, "
                 "unless you had a valid reason (for example health or moving with a partner).")

JOB_GROUPS = [[f"job_{i}_{s}" for s in ("employer", "from", "to")] for i in range(1, MAX_JOBS + 1)]


def _job(i: int) -> list:
    p = f"job_{i}_"
    return [f"Job {i}" + (" (the most recent)" if i == 1 else ""),
            F("Input", p + "employer", f"Job {i}: employer", required=True),
            F("DatePicker", p + "from", f"Job {i}: from", required=True),
            F("DatePicker", p + "to", f"Job {i}: to", required=True)]


FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_you", "1. About you",
      C("Accordion", "acc_you", "Personal details",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "national_id", "National id number (11 digits)", required=True),
        F("Input", "phone", "Phone", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "address", "Home address", required=True))),
    C("Tab", "tab_history", "2. Work history",
      C("Accordion", "acc_history", "Your jobs in the last 3 years",
        "List your jobs starting with the most recent.",
        F("NumberInput", "job_count", "How many jobs? (1 to 5)", required=True),
        *[x for i in range(1, MAX_JOBS + 1) for x in _job(i)]),
      C("Accordion", "acc_leaving", "Leaving your last job",
        F("DatePicker", "last_working_day", "Last working day", required=True),
        F("Dropdown", "leaving_reason", "Why did the job end?", required=True,
          options=opts("dismissed:Dismissed by the employer", "redundancy:Redundancy", "contract_end:Fixed-term contract ended",
                       "mutual:Mutual agreement", "resigned:I resigned", "other:Other")),
        F("TextArea", "leaving_details", "Tell us what happened", required=True),
        F("TextArea", "leaving_notice", "Notice (calculated)", readonly=True),
        F("FileUpload", "termination_letter", "Termination letter or end-of-contract certificate", required=True))),
    C("Tab", "tab_payment", "3. Payment and availability",
      C("Accordion", "acc_bank", "Bank account",
        F("Input", "iban", "IBAN", required=True),
        F("Input", "account_holder", "Account holder", required=True)),
      C("Accordion", "acc_available", "Availability",
        F("Checkbox", "available_for_work", "I am available for work and will look for a job actively", required=True),
        F("Dropdown", "hours_wanted", "Work you are looking for",
          options=opts("full:Full time", "part:Part time", "any:Either")),
        F("Checkbox", "declaration", "I confirm my answers are true and I will report any change", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Unemployment benefit",
    "starters": ["I lost my job, apply for benefit", "I quit my job last week", "What do I need to apply?"],
    "persona": "You are the Norland Employment Service's benefit assistant. Be calm and clear; never promise an amount.",
    "flow_hints": [
        "Ask how many jobs in the last 3 years, then each one starting with the most recent.",
        "When the person resigned, tell them about the possible 12-week delay.",
        "Availability for work is required to receive the benefit.",
    ],
    "glossary": {
        "leaving_notice": "Shown when the person resigned: the benefit may be delayed by 12 weeks.",
        "job_count": "Jobs in the last 3 years, at most 5.",
        "national_id": "11 digits.",
        "available_for_work": "Required: the benefit is paid only to people available for work.",
    },
    "pii": ["first_name", "last_name", "birth_date", "national_id", "phone", "email", "address", "iban", "account_holder"],
}

PAGE = {
    "path": "/lab/norland-unemployment",
    "title": "Norland Employment Service: unemployment benefit",
    "description": "Apply for unemployment benefit with the Norland Employment Service.",
    "keywords": ["unemployment", "benefit", "jobseeker", "lost my job", "employment service", "norland"],
    "sections": [
        {"id": "rules", "title": "Before you apply",
         "text": "Apply after your last working day. Upload your termination letter or end-of-contract certificate. "
                 "If you resigned, the benefit may be delayed by 12 weeks. You must be available for work. "
                 "The benefit is paid monthly to your bank account."},
    ],
}


def rules(h) -> None:
    h.a_date("birth_date", past=True)
    h.match("national_id", r"\d{11}", "A national id number has 11 digits")
    h.phone("phone")
    h.email("email")

    h.number("job_count", lo=1, hi=MAX_JOBS, integer=True, msg="Enter 1 to 5 jobs")
    k = h.repeat("job_count", JOB_GROUPS, required=("_employer", "_from", "_to"))
    for i in range(1, k + 1):
        p = f"job_{i}_"
        h.a_date(p + "from", past=True)
        h.a_date(p + "to", past=True, msg="An end date cannot be in the future")
        a, b = h.date(p + "from"), h.date(p + "to")
        if a and b and b <= a and not h.has_error(p + "to"):
            h.error(p + "to", "The end date must be after the start date")

    h.a_date("last_working_day", past=True, msg="Apply after your last working day")
    r = h.id("leaving_reason")
    h.show("leaving_details", when=r == "other")
    h.require("leaving_details", when=r == "other")
    h.show("leaving_notice", when=r == "resigned")
    h.set("leaving_notice", RESIGN_NOTICE if r == "resigned" else "")
    h.iban("iban")
