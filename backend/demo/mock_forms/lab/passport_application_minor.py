"""Lab form: a passport for a child under 16 at the Norland Passport Office (medium).

Rules: the child is under 16 on the day of the application; a renewal shows the previous passport number (2 letters
and 7 digits) and makes it required; a replacement for a lost or stolen passport asks for the police report number;
the child's height is 40 to 200 cm; both parents consent (parent 2's section is shown) unless one parent has sole
custody, which hides parent 2 and reveals the court order upload (required); fast-track changes the read-only fee:
standard 40 EUR (6 weeks), fast-track 95 EUR (5 working days); collection at an office needs the office.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "passport_application_minor"
SEQUENTIAL = False
FEE_STANDARD, FEE_FAST = 40, 95

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_child", "1. Child",
      C("Accordion", "acc_application", "Application",
        F("RadioGroup", "application_type", "This is", required=True,
          options=opts("first:A first passport", "renewal:A renewal", "replacement:A replacement (lost or stolen)")),
        F("Input", "previous_passport_number", "Previous passport number", required=True, placeholder="NL1234567"),
        F("Input", "police_report_number", "Police report number", required=True)),
      C("Accordion", "acc_child", "The child (under 16)",
        F("Input", "child_surname", "Surname", required=True),
        F("Input", "child_first_names", "First name(s)", required=True),
        F("DatePicker", "child_birth_date", "Date of birth", required=True),
        F("Input", "child_birth_place", "Place of birth", required=True),
        F("RadioGroup", "child_sex", "Sex", required=True, options=opts("f:Female", "m:Male", "x:X")),
        F("NumberInput", "child_height_cm", "Height, cm", required=True),
        F("Dropdown", "eye_colour", "Eye colour", required=True,
          options=opts("brown:Brown", "blue:Blue", "green:Green", "grey:Grey", "hazel:Hazel", "other:Other")),
        F("FileUpload", "child_photo", "Photo of the child (35 x 45 mm)", required=True))),
    C("Tab", "tab_parents", "2. Parents",
      C("Accordion", "acc_custody", "Custody",
        "Both parents consent, unless one parent has sole custody by a court order.",
        F("RadioGroup", "custody", "Parental responsibility", required=True,
          options=opts("joint:Both parents", "sole:One parent has sole custody")),
        F("FileUpload", "court_order", "Court order granting sole custody", required=True)),
      C("Accordion", "acc_parent1", "Parent 1 (applying)",
        F("Input", "parent1_name", "Full name", required=True),
        F("Input", "parent1_id_number", "National id number (11 digits)", required=True),
        F("Input", "parent1_phone", "Phone", required=True),
        F("Input", "parent1_email", "Email", required=True),
        F("Checkbox", "parent1_consent", "I consent to the passport being issued", required=True)),
      C("Accordion", "acc_parent2", "Parent 2",
        F("Input", "parent2_name", "Full name", required=True),
        F("Input", "parent2_id_number", "National id number (11 digits)", required=True),
        F("Input", "parent2_phone", "Phone", required=True),
        F("Checkbox", "parent2_consent", "Parent 2 consents to the passport being issued", required=True))),
    C("Tab", "tab_service", "3. Service and fee",
      C("Accordion", "acc_service", "Processing",
        "Standard: 40 EUR, about 6 weeks. Fast-track: 95 EUR, 5 working days.",
        F("Checkbox", "fast_track", "Fast-track processing"),
        F("Input", "passport_fee", "Fee, EUR (calculated)", readonly=True),
        F("RadioGroup", "collection", "Getting the passport", required=True,
          options=opts("post:Registered post", "office:Collect at an office")),
        F("Dropdown", "collection_office", "Office", required=True,
          options=opts("capital:Norland City", "westmere:Westmere", "harbour:Port Aldis")))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Child passport (under 16)",
    "starters": ["A passport for my 5-year-old", "Renew my daughter's passport", "How much is fast-track?"],
    "persona": "You are the Norland Passport Office's assistant for children's passports. Be friendly and exact.",
    "flow_hints": [
        "Ask whether it is a first passport, a renewal or a replacement first.",
        "Both parents consent unless one has sole custody (then upload the court order).",
        "The fee is calculated: 40 EUR standard, 95 EUR fast-track.",
    ],
    "glossary": {
        "passport_fee": "Standard 40 EUR (about 6 weeks); fast-track 95 EUR (5 working days).",
        "previous_passport_number": "2 letters and 7 digits, e.g. NL1234567.",
        "child_height_cm": "40 to 200 cm.",
        "child_birth_date": "This form is for children under 16.",
        "parent1_id_number": "11 digits.",
    },
    "pii": ["child_birth_date", "parent1_id_number", "parent1_phone", "parent1_email", "parent2_id_number",
            "parent2_phone", "previous_passport_number"],
}

PAGE = {
    "path": "/lab/norland-child-passport",
    "title": "Norland Passport Office: passport for a child",
    "description": "Apply for a Norland passport for a child under 16.",
    "keywords": ["passport", "child passport", "minor", "norland", "travel document", "renewal"],
    "sections": [
        {"id": "fees", "title": "Fees and times",
         "text": "A child's passport costs 40 EUR and takes about 6 weeks. Fast-track costs 95 EUR and takes 5 working "
                 "days. A child's passport is valid for 5 years."},
        {"id": "consent", "title": "Consent",
         "text": "Both parents consent. A parent with sole custody uploads the court order instead of the other "
                 "parent's consent."},
    ],
}


def rules(h) -> None:
    t = h.id("application_type")
    h.show("previous_passport_number", when=t == "renewal")
    h.require("previous_passport_number", when=t == "renewal")
    h.match("previous_passport_number", r"[A-Za-z]{2}\d{7}", "A passport number has 2 letters and 7 digits, e.g. NL1234567")
    h.show("police_report_number", when=t == "replacement")
    h.require("police_report_number", when=t == "replacement")

    h.a_date("child_birth_date", past=True)
    age = h.age("child_birth_date")
    if age is not None and age >= 16 and not h.has_error("child_birth_date"):
        h.error("child_birth_date", "This form is for children under 16; from 16 use the adult form")
    h.number("child_height_cm", lo=40, hi=200, msg="Enter a height from 40 to 200 cm")

    sole = h.id("custody") == "sole"
    p2 = ["parent2_name", "parent2_id_number", "parent2_phone", "parent2_consent"]
    h.show("acc_parent2", *p2, when=not sole)
    h.require(*p2, when=not sole)
    h.show("court_order", when=sole)
    h.require("court_order", when=sole)
    for n in ("parent1_id_number", "parent2_id_number"):
        h.match(n, r"\d{11}", "A national id number has 11 digits")
    h.phone("parent1_phone")
    h.phone("parent2_phone")
    h.email("parent1_email")

    h.set("passport_fee", str(FEE_FAST if h.on("fast_track") else FEE_STANDARD))
    office = h.id("collection") == "office"
    h.show("collection_office", when=office)
    h.require("collection_office", when=office)
