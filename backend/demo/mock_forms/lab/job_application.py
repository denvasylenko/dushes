"""Lab form: an application for a Backend Developer opening (repeating work history, a range, a read-only notice).

Rules: work history is a repeating group of up to 4 jobs; ticking "I work here now" hides and un-requires the
end date; an end date cannot be before the start date; only one job can be the current one; the salary range
needs a minimum no higher than the maximum (both 30000 to 200000 EUR); answering "yes" to visa sponsorship shows
a read-only notice that the company does not sponsor visas for this role; the CV upload is required; the cover
letter is optional (at most 3000 characters); "Other" skill shows a free-text field.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "job_application"

MAX_JOBS = 4
VISA_NOTICE = ("Brightwire Systems does not sponsor work visas for this role. You can still apply if you already "
               "have the right to work in the Netherlands.")


def _job(i: int) -> list:
    return [F("Input", f"job_{i}_title", f"Job {i}: title", required=True),
            F("Input", f"job_{i}_company", f"Job {i}: company", required=True),
            F("DatePicker", f"job_{i}_from", f"Job {i}: from", required=True),
            F("Checkbox", f"job_{i}_current", f"Job {i}: I work here now"),
            F("DatePicker", f"job_{i}_to", f"Job {i}: to", required=True)]


JOB_GROUPS = [[f"job_{i}_title", f"job_{i}_company", f"job_{i}_from", f"job_{i}_current", f"job_{i}_to"]
              for i in range(1, MAX_JOBS + 1)]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_personal", "Personal",
      C("Accordion", "acc_personal", "About you",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Phone", required=True, placeholder="+31 6 12345678"),
        F("Input", "city", "City you live in", required=True),
        F("Input", "linkedin", "LinkedIn or portfolio URL"))),
    C("Tab", "tab_experience", "Experience",
      C("Accordion", "acc_jobs", "Work history",
        "List up to 4 recent jobs, newest first.",
        F("NumberInput", "job_count", "How many jobs will you list? (0 to 4)", required=True),
        *[f for i in range(1, MAX_JOBS + 1) for f in _job(i)]),
      C("Accordion", "acc_education", "Education",
        F("Dropdown", "education_level", "Highest education", required=True,
          options=opts("school:Secondary school", "bachelor:Bachelor's degree", "master:Master's degree",
                       "phd:PhD", "bootcamp:Bootcamp or self-taught")),
        F("Input", "field_of_study", "Field of study", required=True),
        F("Input", "institution", "School or university", required=True),
        F("NumberInput", "graduation_year", "Year finished"))),
    C("Tab", "tab_skills", "Skills",
      C("Accordion", "acc_skills", "Skills",
        F("MultiSelect", "skills", "Skills", required=True,
          options=opts("python:Python", "go:Go", "java:Java", "postgres:PostgreSQL", "kafka:Kafka",
                       "k8s:Kubernetes", "aws:AWS", "other:Other")),
        F("Input", "other_skills", "Other skills", required=True),
        F("NumberInput", "years_backend", "Years of backend experience", required=True))),
    C("Tab", "tab_terms", "Terms",
      C("Accordion", "acc_salary", "Salary and availability",
        "The role pays 55000 to 85000 EUR a year, depending on experience.",
        F("NumberInput", "salary_min", "Expected salary from (EUR a year)", required=True),
        F("NumberInput", "salary_max", "Expected salary to (EUR a year)", required=True),
        F("Dropdown", "notice_period", "Notice period", required=True,
          options=opts("none:Available now", "2w:2 weeks", "1m:1 month", "2m:2 months", "3m:3 months or more"))),
      C("Accordion", "acc_visa", "Right to work",
        F("RadioGroup", "visa_sponsorship", "Will you need visa sponsorship?", required=True,
          options=opts("no:No, I can already work in the Netherlands", "yes:Yes")),
        F("TextArea", "visa_notice", "About visa sponsorship", readonly=True))),
    C("Tab", "tab_documents", "Documents",
      C("Accordion", "acc_documents", "CV and cover letter",
        F("FileUpload", "cv", "CV (PDF)", required=True),
        F("TextArea", "cover_letter", "Cover letter (optional)"),
        F("Checkbox", "privacy", "I agree that my application is kept for 6 months", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Backend Developer at Brightwire Systems",
    "starters": ["I want to apply for the backend role", "Do you sponsor visas?", "What does the role pay?"],
    "persona": "You are Brightwire Systems' recruiting assistant. Be friendly and factual; never promise an interview.",
    "flow_hints": [
        "Personal details first, then up to 4 jobs, education, skills, salary and the CV.",
        "For the current job, tick 'I work here now' instead of giving an end date.",
        "The company does not sponsor visas for this role: say so plainly if asked.",
        "The CV is required; the cover letter is optional.",
    ],
    "glossary": {
        "salary_min": "The lower end of your expected yearly gross salary in EUR; the role pays 55000 to 85000 EUR.",
        "visa_sponsorship": "Brightwire Systems does not sponsor work visas for this role.",
        "notice_period": "How soon you could start after accepting an offer.",
        "cv": "Your CV as a PDF.",
    },
    "pii": ["email", "phone", "linkedin"],
}

PAGE = {
    "path": "/lab/backend-job",
    "title": "Brightwire Systems: Backend Developer",
    "description": "Brightwire Systems' application form for the Backend Developer opening in Utrecht.",
    "keywords": ["job", "career", "developer", "backend", "apply", "vacancy", "hiring", "cv"],
    "sections": [
        {"id": "role", "title": "The role",
         "text": "Backend Developer in Utrecht, hybrid (3 days in the office). Python and PostgreSQL, Kafka a plus. "
                 "Salary 55000 to 85000 EUR a year, depending on experience."},
        {"id": "visa", "title": "Right to work",
         "text": "We do not sponsor work visas for this role: you need the right to work in the Netherlands."},
        {"id": "apply", "title": "How to apply",
         "text": "Send your work history (up to 4 jobs), your CV as a PDF and, if you like, a cover letter."},
    ],
}


def rules(h) -> None:
    h.email("email")
    h.phone("phone")
    h.match("linkedin", r"(https?://)?[\w.-]+\.[a-z]{2,}(/\S*)?", "Enter a web address, like linkedin.com/in/you")

    h.number("job_count", 0, MAX_JOBS, msg="List 0 to 4 jobs", integer=True)
    k = h.repeat("job_count", JOB_GROUPS, required=("_title", "_company", "_from", "_to"))
    current = 0
    for i in range(1, MAX_JOBS + 1):
        h.a_date(f"job_{i}_from", past=True, msg="A start date cannot be in the future")
        now = h.on(f"job_{i}_current")
        if i <= k:
            current += now
            h.show(f"job_{i}_to", when=not now)
            h.require(f"job_{i}_to", when=not now)
            if not now:
                h.a_date(f"job_{i}_to", past=True, after=h.date(f"job_{i}_from"),
                         msg="The end date must be after the start date")
    if current > 1:
        h.error("job_count", "Only one job can be your current one")

    h.number("graduation_year", 1960, 2030, integer=True)
    h.show("other_skills", when="other" in h.ids("skills"))
    h.require("other_skills", when="other" in h.ids("skills"))
    h.number("years_backend", 0, 50)

    for n in ("salary_min", "salary_max"):
        h.number(n, 30000, 200000)
    lo, hi = h.num("salary_min"), h.num("salary_max")
    if lo is not None and hi is not None and lo > hi and not h.has_error("salary_max"):
        h.error("salary_max", "The upper end must not be lower than the lower end")

    needs = h.id("visa_sponsorship") == "yes"
    h.show("visa_notice", when=needs)
    if needs:
        h.set("visa_notice", VISA_NOTICE)
    h.length("cover_letter", 0, 3000, msg="Keep the cover letter under 3000 characters")
