"""Lab form: "change my deputy" in a company's staff portal (tiny; the page never shows it: it is filled in the chat).

Rules: the deputy's email must look like an email address; the start date is today or later.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "deputy_change"

FORM = C(
    "Accordion", "deputy", "Change my deputy",
    "Who stands in for you, from when and why.",
    F("Input", "deputy_name", "Deputy's full name", required=True),
    F("Input", "deputy_email", "Deputy's work email", required=True, placeholder="name@northwind.example"),
    F("DatePicker", "start_date", "Start date", required=True),
    F("Dropdown", "reason", "Reason", required=True,
      options=opts("vacation:Vacation", "leave:Leave", "permanent:Permanent change")),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Change my deputy",
    "starters": ["Can I change my deputy?", "Who is my deputy now?"],
    "persona": "You are the Northwind staff portal's assistant. Short and practical.",
    "flow_hints": [
        "The person does not see this form: the page shows only this chat. Collect every value here with cards and "
        "never point at a field, a button or a form on the page.",
        "When all four values are set, send the change with submit_deputy_change.",
    ],
    "glossary": {"reason": "Vacation and leave are temporary; a permanent change replaces the deputy until changed again."},
    "pii": ["deputy_email"],
}

PAGE = {
    "path": "/lab/staff-portal",
    "title": "Northwind staff portal",
    "description": "Northwind's staff portal: ask the assistant to change who stands in for you while you are away.",
    "keywords": ["deputy", "stand-in", "substitute", "vacation", "leave", "staff", "portal"],
    "sections": [{"id": "deputy", "title": "Your deputy",
                  "text": "A deputy approves requests for you while you are away. To change your deputy, tell the "
                          "assistant the person's name, their work email, the start date and the reason."}],
}


def rules(h) -> None:
    h.email("deputy_email")
    h.a_date("start_date", future=True)
