"""Lab form: a rental application for one listed flat (rent 1450 EUR a month), four tabs that unlock one by one.

Rules: the rent may be at most 40% of the combined monthly net income of the applicant and the co-applicants
(at least 3625 EUR together; the error sits on the co-applicant count so it can be fixed by adding one);
co-applicants are a repeating group of up to 3; dogs are not allowed in this flat; other pets need a description;
the move-in date is at least 7 days from today; two references, each with a name, a phone and a relationship;
the payslips upload is required. The combined income is shown read-only.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "apartment_rental"
SEQUENTIAL = True

RENT = 1450
MAX_SHARE = 0.40
MAX_CO = 3

RELATIONS = opts("partner:Partner or spouse", "flatmate:Flatmate", "family:Family member", "guarantor:Guarantor")


def _co(i: int) -> list:
    return [F("Input", f"co_{i}_name", f"Co-applicant {i}: full name", required=True),
            F("Dropdown", f"co_{i}_relation", f"Co-applicant {i}: relationship to you", required=True, options=RELATIONS),
            F("Input", f"co_{i}_email", f"Co-applicant {i}: email", required=True),
            F("NumberInput", f"co_{i}_income", f"Co-applicant {i}: monthly net income (EUR)", required=True)]


def _ref(i: int) -> list:
    return [F("Input", f"ref_{i}_name", f"Reference {i}: full name", required=True),
            F("Input", f"ref_{i}_phone", f"Reference {i}: phone", required=True),
            F("Dropdown", f"ref_{i}_relation", f"Reference {i}: who they are", required=True,
              options=opts("landlord:Previous landlord", "employer:Employer", "other:Other"))]


CO_GROUPS = [[f"co_{i}_name", f"co_{i}_relation", f"co_{i}_email", f"co_{i}_income"] for i in range(1, MAX_CO + 1)]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_applicant", "1. Applicant",
      C("Accordion", "acc_applicant", "About you",
        "Flat 4B, 12 Canal Row: 2 rooms, 64 m2, rent 1450 EUR a month plus a deposit of two months' rent.",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Mobile phone", required=True, placeholder="+31 6 12345678"),
        F("Dropdown", "employment", "Employment", required=True,
          options=opts("employed:Employed", "self:Self-employed", "student:Student", "retired:Retired")),
        F("Input", "employer", "Employer", required=True),
        F("NumberInput", "monthly_income", "Your monthly net income (EUR)", required=True))),
    C("Tab", "tab_co", "2. Co-applicants",
      C("Accordion", "acc_co", "People applying with you",
        "The rent may be at most 40% of the combined monthly net income of everyone on the application.",
        F("NumberInput", "co_applicant_count", "How many co-applicants? (0 to 3)", required=True),
        *[f for i in range(1, MAX_CO + 1) for f in _co(i)],
        F("Input", "combined_income", "Combined monthly net income (EUR, calculated)", readonly=True))),
    C("Tab", "tab_household", "3. Household and move-in",
      C("Accordion", "acc_household", "Household",
        F("NumberInput", "occupants", "People who will live in the flat", required=True),
        F("RadioGroup", "pets", "Pets", required=True,
          options=opts("none:No pets", "cat:Cat", "dog:Dog", "other:Other small pet")),
        F("Input", "pet_details", "Which pet, and how many?", required=True),
        F("Checkbox", "smoker", "Someone in the household smokes")),
      C("Accordion", "acc_move", "Move-in",
        "The earliest move-in is 7 days after the application.",
        F("DatePicker", "move_in_date", "Move-in date", required=True),
        F("Dropdown", "lease_term", "Lease term", required=True,
          options=opts("12:12 months", "24:24 months", "open:Open-ended"))),
      ),
    C("Tab", "tab_refs", "4. References and documents",
      C("Accordion", "acc_refs", "Two references",
        *_ref(1), *_ref(2)),
      C("Accordion", "acc_docs", "Documents",
        "Upload your last three payslips (PDF or photos).",
        F("FileUpload", "payslips", "Payslips", required=True),
        F("TextArea", "message", "A note for the landlord"),
        F("Checkbox", "consent", "I confirm the information is true and agree to a credit check", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Rental application: Flat 4B, 12 Canal Row",
    "starters": ["I want to apply for the flat", "Can I apply with my partner?", "Are pets allowed?"],
    "persona": "You are Canalside Lettings' application assistant. Be clear and fair; never promise that an application will be accepted.",
    "flow_hints": [
        "The tabs unlock one by one: applicant, co-applicants, household and move-in, references and documents.",
        "The rent of 1450 EUR may be at most 40% of the combined net income: at least 3625 EUR a month together.",
        "If the applicant's income alone is too low, suggest adding a co-applicant (up to 3).",
        "Dogs are not allowed in this flat; cats and small pets are.",
        "The move-in date is at least 7 days from today.",
    ],
    "glossary": {
        "monthly_income": "Net (after tax) income per month, in EUR.",
        "co_applicant_count": "0 to 3 people applying together with you; their incomes count towards the 40% rule.",
        "pets": "Dogs are not allowed in this flat. Cats and other small pets are fine.",
        "move_in_date": "At least 7 days after today.",
        "payslips": "The last three payslips.",
    },
    "pii": ["birth_date", "email", "phone", "monthly_income", "co_1_email", "co_2_email", "co_3_email",
            "ref_1_phone", "ref_2_phone"],
}

PAGE = {
    "path": "/lab/canal-flat",
    "title": "Canalside Lettings: Flat 4B, 12 Canal Row",
    "description": "Canalside Lettings' rental application for Flat 4B, 12 Canal Row.",
    "keywords": ["flat", "apartment", "rent", "rental", "lease", "letting", "landlord"],
    "sections": [
        {"id": "listing", "title": "The flat",
         "text": "Flat 4B, 12 Canal Row: 2 rooms, 64 m2, third floor with a lift. Rent 1450 EUR a month, "
                 "deposit two months' rent (2900 EUR). Available from 7 days after your application."},
        {"id": "rules", "title": "Who can apply",
         "text": "The rent may be at most 40% of the combined monthly net income of everyone on the application, "
                 "so at least 3625 EUR a month together. You can apply with up to 3 co-applicants. "
                 "Dogs are not allowed in this flat; cats and small pets are welcome. "
                 "We need two references and your last three payslips."},
    ],
}


def rules(h) -> None:
    h.a_date("birth_date", past=True)
    age = h.age("birth_date")
    if age is not None and age < 18:
        h.error("birth_date", "The applicant must be at least 18")
    h.email("email")
    h.phone("phone")
    works = h.id("employment") in ("employed", "self")
    h.show("employer", when=works)
    h.require("employer", when=works)
    h.number("monthly_income", 0, 1_000_000)

    h.number("co_applicant_count", 0, MAX_CO, msg="Enter 0 to 3 co-applicants", integer=True)
    k = h.repeat("co_applicant_count", CO_GROUPS, required=("_name", "_relation", "_email", "_income"))
    for i in range(1, MAX_CO + 1):
        h.email(f"co_{i}_email")
        h.number(f"co_{i}_income", 0, 1_000_000)
    own = h.num("monthly_income")
    if own is not None:
        total = own + sum(h.num(f"co_{i}_income") or 0 for i in range(1, k + 1))
        h.set("combined_income", round(total, 2))
        if h.text("co_applicant_count") and not h.has_error("co_applicant_count") and RENT > MAX_SHARE * total:
            h.error("co_applicant_count",
                    f"The rent is more than 40% of the combined income ({round(total)} EUR); together you need "
                    "at least 3625 EUR a month: add a co-applicant or check the incomes")

    h.number("occupants", 1, 6, msg="The flat is for 1 to 6 people", integer=True)
    pet = h.id("pets")
    if pet == "dog":
        h.error("pets", "Dogs are not allowed in this flat")
    h.show("pet_details", when=pet in ("cat", "other"))
    h.require("pet_details", when=pet in ("cat", "other"))
    h.a_date("move_in_date", after=date.today() + timedelta(days=7),
             msg="The move-in date must be at least 7 days from today")

    for i in (1, 2):
        h.phone(f"ref_{i}_phone")
    if h.text("ref_1_name") and h.text("ref_1_name").lower() == h.text("ref_2_name").lower():
        h.error("ref_2_name", "Give two different references")
