"""Lab form: a renovation permit application at the City of Westmere planning office (medium).

Cadastral parcel numbers look like WM-042-1187: "WM", a 3-digit section, a 4-digit parcel, an optional letter for a
split parcel (WM-042-1187B).

Rules: the parcel number has that format; an agent applying for the owner gives the agency details and uploads the
owner's signed authorisation; structural works make the structural engineer's name and licence number (ENG- and
5 digits) required; an extension needs its floor area (1 to 40 m2; larger extensions need a full building permit);
demolition needs the asbestos survey upload; the read-only fee is 1% of the estimated cost, at least 150 and at most
5,000 EUR; works start at least 30 days from today and last 1 to 36 months.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "building_permit"
SEQUENTIAL = False

FEE_RATE, FEE_MIN, FEE_MAX, LEAD_DAYS = 0.01, 150, 5000, 30

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_property", "1. Property and applicant",
      C("Accordion", "acc_property", "Property",
        F("Input", "property_street", "Street and number", required=True),
        F("Input", "property_postcode", "Postcode (5 digits)", required=True),
        F("Input", "parcel_number", "Cadastral parcel number", required=True, placeholder="WM-042-1187"),
        F("Dropdown", "property_type", "Building type", required=True,
          options=opts("house:Detached or semi-detached house", "flat:Flat in a block", "commercial:Shop or office",
                       "outbuilding:Garage or outbuilding")),
        F("Checkbox", "listed_building", "The building is listed (heritage protected)")),
      C("Accordion", "acc_applicant", "Applicant",
        F("RadioGroup", "applicant_role", "I apply as", required=True,
          options=opts("owner:The owner", "agent:An agent for the owner (architect, contractor)")),
        F("Input", "owner_name", "Owner's full name", required=True),
        F("Input", "owner_phone", "Owner's phone", required=True),
        F("Input", "owner_email", "Owner's email", required=True),
        F("Input", "agent_name", "Agent's full name", required=True),
        F("Input", "agent_company", "Agent's firm", required=True),
        F("Input", "agent_phone", "Agent's phone", required=True),
        F("Input", "agent_email", "Agent's email", required=True),
        F("FileUpload", "owner_authorisation", "Owner's signed authorisation", required=True))),
    C("Tab", "tab_works", "2. Works",
      C("Accordion", "acc_works", "What you will do",
        F("MultiSelect", "works_types", "Type of works", required=True,
          options=opts("interior:Interior refit", "roof:Roof", "facade:Facade or cladding", "windows:Windows and doors",
                       "extension:Extension", "structural:Structural (load-bearing walls, floors, foundations)",
                       "demolition:Partial demolition")),
        F("TextArea", "works_description", "Describe the works", required=True),
        F("NumberInput", "extension_area", "Extension floor area, m2", required=True),
        F("FileUpload", "asbestos_survey", "Asbestos survey", required=True),
        F("FileUpload", "plans", "Plans and drawings (PDF)", required=True)),
      C("Accordion", "acc_engineer", "Structural engineer",
        "Structural works need a licensed structural engineer.",
        F("Input", "engineer_name", "Engineer's full name", required=True),
        F("Input", "engineer_licence", "Engineer's licence number", required=True, placeholder="ENG-12345"))),
    C("Tab", "tab_schedule", "3. Cost and schedule",
      C("Accordion", "acc_cost", "Cost and fee",
        "The permit fee is 1% of the estimated cost, at least 150 EUR and at most 5,000 EUR.",
        F("NumberInput", "estimated_cost", "Estimated cost of the works, EUR", required=True),
        F("Input", "permit_fee", "Permit fee, EUR (calculated)", readonly=True)),
      C("Accordion", "acc_schedule", "Schedule",
        "Works can start at least 30 days after the application.",
        F("DatePicker", "start_date", "Planned start", required=True),
        F("NumberInput", "duration_months", "Expected duration, months", required=True),
        F("Checkbox", "declaration", "I confirm the information is correct and the owner agrees to the works",
          required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Renovation permit",
    "starters": ["I want to renovate my roof", "Apply for a permit for my client", "How much is the permit fee?"],
    "persona": "You are the City of Westmere planning office's assistant. Be practical and exact; never approve works yourself.",
    "flow_hints": [
        "Ask whether the applicant is the owner or an agent first: an agent uploads the owner's authorisation.",
        "Structural works need the structural engineer's name and licence number.",
        "The fee is calculated from the estimated cost: never ask the user for it.",
    ],
    "glossary": {
        "parcel_number": "WM, a 3-digit section and a 4-digit parcel, e.g. WM-042-1187 (a split parcel adds a letter: WM-042-1187B).",
        "engineer_licence": "ENG- followed by 5 digits, e.g. ENG-12345.",
        "permit_fee": "1% of the estimated cost, at least 150 EUR and at most 5,000 EUR.",
        "start_date": "At least 30 days from the day of the application.",
        "extension_area": "1 to 40 m2; a larger extension needs a full building permit.",
        "duration_months": "1 to 36 months.",
    },
    "pii": ["owner_name", "owner_phone", "owner_email", "agent_name", "agent_phone", "agent_email"],
}

PAGE = {
    "path": "/lab/westmere-permit",
    "title": "City of Westmere: renovation permit",
    "description": "Apply for a renovation permit with the City of Westmere planning office.",
    "keywords": ["building permit", "renovation", "planning", "westmere", "construction", "works"],
    "sections": [
        {"id": "fee", "title": "Fee",
         "text": "The permit fee is 1% of the estimated cost of the works, at least 150 EUR and at most 5,000 EUR."},
        {"id": "rules", "title": "Rules",
         "text": "Works start at least 30 days after the application. Structural works need a licensed structural "
                 "engineer. Extensions up to 40 m2 use this form; larger ones need a full building permit. "
                 "An agent applying for the owner uploads the owner's signed authorisation."},
    ],
}


def rules(h) -> None:
    h.match("property_postcode", r"\d{5}", "A postcode has 5 digits")
    h.match("parcel_number", r"(?i)WM-\d{3}-\d{4}[A-Z]?", "A parcel number looks like WM-042-1187")
    agent = h.id("applicant_role") == "agent"
    a = ["agent_name", "agent_company", "agent_phone", "agent_email", "owner_authorisation"]
    h.show(*a, when=agent)
    h.require(*a, when=agent)
    for n in ("owner_phone", "agent_phone"):
        h.phone(n)
    for n in ("owner_email", "agent_email"):
        h.email(n)

    works = set(h.ids("works_types"))
    st = "structural" in works
    h.show("acc_engineer", "engineer_name", "engineer_licence", when=st)
    h.require("engineer_name", "engineer_licence", when=st)
    h.match("engineer_licence", r"(?i)ENG-\d{5}", "An engineer's licence number looks like ENG-12345")
    ext = "extension" in works
    h.show("extension_area", when=ext)
    h.require("extension_area", when=ext)
    h.number("extension_area", lo=1, hi=40, msg="This form covers extensions of 1 to 40 m2; larger ones need a full permit")
    demo = "demolition" in works
    h.show("asbestos_survey", when=demo)
    h.require("asbestos_survey", when=demo)

    h.number("estimated_cost", lo=1, msg="Enter the estimated cost in EUR")
    cost = h.num("estimated_cost")
    if cost is not None and cost > 0 and not h.has_error("estimated_cost"):
        h.set("permit_fee", str(round(min(max(cost * FEE_RATE, FEE_MIN), FEE_MAX))))
    earliest = date.today() + timedelta(days=LEAD_DAYS)
    h.a_date("start_date", after=earliest,
             msg=f"Works can start 30 days from today at the earliest ({earliest.isoformat()})")
    h.number("duration_months", lo=1, hi=36, integer=True, msg="Enter 1 to 36 months")
