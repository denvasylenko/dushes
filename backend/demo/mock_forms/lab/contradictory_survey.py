"""Lab form: a housing association tenant survey that contradicts itself (to test how the assistant handles a
form whose texts disagree with its rules).

The contradictions, on purpose:
- the static text says "All fields are optional", yet the tenancy reference, name, age, date of birth, years in
  the home and overall satisfaction are required;
- "Tenancy reference (optional)" is required;
- "Phone (required)" is optional;
- the double-negative checkbox "Untick if you do not want to not receive letters": ticked means letters are sent,
  unticked means no letters (it starts unticked);
- both "Age" and "Date of birth" are asked and must agree (an error on the age when they do not);
- "How long have you lived in your home?" has overlapping options: "1-2 years", "2-5 years", "5+ years" and
  "more than 2 years".

Rules: the tenancy reference is T + 6 digits; the age is a whole number 16-120 that must equal the age computed from
the date of birth; the date of birth is in the past; email and phone are validated when given; a repairs comment is
required when the repairs rating is "poor".
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "contradictory_survey"

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_you", "About you",
      C("Accordion", "acc_you", "Your details",
        "All fields are optional.",
        F("Input", "tenancy_ref", "Tenancy reference (optional)", required=True, placeholder="T123456"),
        F("Input", "full_name", "Full name", required=True),
        F("NumberInput", "age", "Age", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "phone", "Phone (required)"),
        F("Input", "email", "Email"),
        F("Checkbox", "letters", "Untick if you do not want to not receive letters"))),
    C("Tab", "tab_home", "Your home",
      C("Accordion", "acc_home", "Living here",
        "All fields are optional.",
        F("RadioGroup", "years_in_home", "How long have you lived in your home?", required=True,
          options=opts("y1_2:1-2 years", "y2_5:2-5 years", "y5p:5+ years", "gt2:more than 2 years")),
        F("RadioGroup", "satisfaction", "Overall, how satisfied are you with Greywell as your landlord?", required=True,
          options=opts("1:Very dissatisfied", "2:Dissatisfied", "3:Neutral", "4:Satisfied", "5:Very satisfied")),
        F("Dropdown", "repairs_rating", "How were repairs handled in the last 12 months?",
          options=opts("good:Good", "ok:Acceptable", "poor:Poor", "none:No repairs needed")),
        F("TextArea", "repairs_comment", "Tell us about the repairs"),
        F("TextArea", "comments", "Anything else?"))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Tenant satisfaction survey",
    "starters": ["I want to fill in the tenant survey", "Is everything really optional?", "I've lived here 3 years"],
    "persona": "You are Greywell Housing Association's survey assistant. Be patient and plain-spoken.",
    "flow_hints": [
        "Despite the text, the backend requires the tenancy reference, name, age, date of birth, years in the home and satisfaction.",
        "Age and date of birth must agree.",
        "The letters checkbox: ticked means the tenant gets letters.",
    ],
    "glossary": {
        "tenancy_ref": "On the tenancy agreement and rent statements: T followed by 6 digits. Required, despite the label.",
        "letters": "Ticked: Greywell sends you letters by post. Unticked: no letters.",
        "years_in_home": "The options overlap; pick the most precise one that fits.",
    },
    "pii": ["tenancy_ref", "full_name", "birth_date", "phone", "email"],
}

PAGE = {
    "path": "/lab/tenant-survey",
    "title": "Greywell Housing Association: tenant survey",
    "description": "Greywell Housing Association's yearly tenant satisfaction survey.",
    "keywords": ["housing", "tenant", "landlord", "survey", "repairs", "rent"],
    "sections": [{"id": "survey", "title": "The yearly survey",
                  "text": "Tell us how we are doing as your landlord. Your tenancy reference (T and 6 digits) is on "
                          "your rent statement. The survey closes at the end of the month."}],
}


def rules(h) -> None:
    h.match("tenancy_ref", r"[Tt]\d{6}", "Use T followed by 6 digits (see your rent statement)")
    h.number("age", 16, 120, integer=True, msg="Enter an age from 16 to 120")
    h.a_date("birth_date", past=True)
    real = h.age("birth_date")
    a = h.num("age")
    if real is not None and a is not None and not h.has_error("age") and int(a) != real:
        h.error("age", f"Your age does not match your date of birth (that makes you {real})")
    h.phone("phone")
    h.email("email")
    h.require("repairs_comment", when=h.id("repairs_rating") == "poor")
