"""Lab form: a residence permit application at the (fictional) Prefecture of Val-d'Aurore, French style (medium-big).

English labels, French formats: phones +33 followed by 9 digits (the first 1-9), 5-digit postcodes, dates written
DD/MM/YYYY on the page, a 14-digit SIRET for employers.

Rules: the permit type (student, worker, family, visitor) shows its own section and required documents; the current
visa must still be valid (expiry in the future) and the passport too; a student shows funds of at least 615 EUR per
month, a visitor at least 1,400 EUR per month; a worker's SIRET has 14 digits; a visitor ticks the no-work pledge; the
proof of address is always required and a host's ID copy is needed when the proof is a host certificate; the
read-only stamp fee is 75 EUR for students and 225 EUR for the other permits.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "residence_permit"
SEQUENTIAL = True

FEES = {"student": 75, "worker": 225, "family": 225, "visitor": 225}
STUDENT_MIN, VISITOR_MIN = 615, 1400

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_identity", "1. Identity and address",
      C("Accordion", "acc_identity", "Identity",
        F("Input", "surname", "Surname", required=True),
        F("Input", "given_names", "Given names", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "birth_place", "Place and country of birth", required=True),
        F("Input", "nationality", "Nationality", required=True),
        F("RadioGroup", "sex", "Sex", required=True, options=opts("f:Female", "m:Male")),
        F("Input", "phone", "Mobile phone (+33)", required=True, placeholder="+33 6 12 34 56 78"),
        F("Input", "email", "Email", required=True)),
      C("Accordion", "acc_address", "Address in France",
        F("Input", "street", "Number and street", required=True),
        F("Input", "postcode", "Postcode (5 digits)", required=True, placeholder="75011"),
        F("Input", "city", "Town", required=True),
        F("Dropdown", "address_proof_type", "Proof of address", required=True,
          options=opts("bill:Utility bill under 3 months old", "rent:Rent receipt or lease",
                       "host:Host certificate (attestation d'hebergement)")),
        F("FileUpload", "address_proof", "Upload the proof of address", required=True),
        F("FileUpload", "host_id_copy", "Copy of your host's ID", required=True))),
    C("Tab", "tab_status", "2. Current visa and passport",
      C("Accordion", "acc_visa", "Your current visa",
        "Apply while your current visa is still valid.",
        F("Dropdown", "current_visa_type", "Current visa", required=True,
          options=opts("vls_ts:Long-stay visa (VLS-TS)", "permit:Residence permit (renewal)", "other:Other")),
        F("Input", "current_visa_number", "Visa or permit number", required=True),
        F("DatePicker", "current_visa_expiry", "Valid until", required=True),
        F("Input", "passport_number", "Passport number", required=True),
        F("DatePicker", "passport_expiry", "Passport valid until", required=True))),
    C("Tab", "tab_permit", "3. Permit",
      C("Accordion", "acc_type", "Permit you apply for",
        F("RadioGroup", "permit_type", "Permit type", required=True,
          options=opts("student:Student", "worker:Employee", "family:Private and family life", "visitor:Visitor")),
        F("Input", "stamp_fee", "Stamp fee, EUR (calculated)", readonly=True)),
      C("Accordion", "acc_student", "Studies",
        F("Input", "school_name", "School or university", required=True),
        F("Input", "course_name", "Course", required=True),
        F("DatePicker", "course_start", "Course start", required=True),
        F("NumberInput", "student_funds", "Monthly resources, EUR", required=True),
        F("FileUpload", "enrolment_certificate", "Certificate of enrolment", required=True),
        F("FileUpload", "student_funds_proof", "Proof of resources (bank statement or grant)", required=True)),
      C("Accordion", "acc_worker", "Employment",
        F("Input", "employer_name", "Employer", required=True),
        F("Input", "employer_siret", "Employer's SIRET (14 digits)", required=True),
        F("Input", "job_title", "Job title", required=True),
        F("Dropdown", "contract_type", "Contract", required=True,
          options=opts("cdi:Permanent (CDI)", "cdd:Fixed-term (CDD)")),
        F("NumberInput", "monthly_salary", "Gross monthly salary, EUR", required=True),
        F("FileUpload", "work_contract", "Signed work contract", required=True),
        F("FileUpload", "work_authorisation", "Work authorisation", required=True)),
      C("Accordion", "acc_family", "Family ties",
        F("Input", "family_member_name", "Family member's full name", required=True),
        F("Dropdown", "family_relation", "Relationship", required=True,
          options=opts("spouse:Spouse of a French citizen", "pacs:PACS partner", "parent:Parent of a French child")),
        F("Input", "family_member_nationality", "Family member's nationality", required=True),
        F("FileUpload", "family_status_doc", "Marriage, PACS or birth certificate", required=True)),
      C("Accordion", "acc_visitor", "Visitor",
        F("NumberInput", "visitor_resources", "Monthly resources, EUR", required=True),
        F("FileUpload", "visitor_resources_proof", "Proof of resources", required=True),
        F("FileUpload", "health_insurance_proof", "Health insurance certificate", required=True),
        F("Checkbox", "no_work_pledge", "I will not work in France", required=True)),
      C("Accordion", "acc_declaration", "Declaration",
        F("Checkbox", "declaration", "I certify that the information is accurate", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Residence permit application",
    "starters": ["I need a student residence permit", "My visa expires next month", "What does the permit cost?"],
    "persona": "You are the Prefecture of Val-d'Aurore's online assistant for residence permits. Be formal and exact; "
               "dates are written DD/MM/YYYY.",
    "flow_hints": [
        "The tabs unlock one by one: identity and address, current visa and passport, permit.",
        "Ask the permit type early: each type has its own section and documents.",
        "An expired visa cannot be used to apply online.",
    ],
    "glossary": {
        "phone": "French format: +33 then 9 digits, e.g. +33 6 12 34 56 78.",
        "postcode": "5 digits, e.g. 75011.",
        "stamp_fee": "75 EUR for a student permit, 225 EUR for the others (paid in tax stamps).",
        "student_funds": "At least 615 EUR per month.",
        "visitor_resources": "At least 1,400 EUR per month.",
        "employer_siret": "The 14-digit company number.",
        "current_visa_expiry": "Must still be valid on the day you apply.",
    },
    "pii": ["surname", "given_names", "birth_date", "phone", "email", "street", "passport_number", "current_visa_number"],
}

PAGE = {
    "path": "/lab/val-daurore-permit",
    "title": "Prefecture of Val-d'Aurore: residence permit",
    "description": "Apply online for a residence permit at the Prefecture of Val-d'Aurore.",
    "keywords": ["residence permit", "titre de sejour", "prefecture", "france", "visa", "student", "worker"],
    "sections": [
        {"id": "when", "title": "When to apply",
         "text": "Apply while your current visa is valid: if it expires on 30/06/2027, apply by 29/06/2027 at the latest. "
                 "Dates are written DD/MM/YYYY."},
        {"id": "fees", "title": "Fees and resources",
         "text": "The stamp fee is 75 EUR for a student permit and 225 EUR for an employee, family or visitor permit. "
                 "Students show at least 615 EUR of resources per month, visitors at least 1,400 EUR per month."},
        {"id": "docs", "title": "Documents",
         "text": "Everyone uploads a proof of address (bill under 3 months old, rent receipt or host certificate; with a "
                 "host certificate add your host's ID). Students: enrolment certificate and proof of resources. "
                 "Employees: work contract and work authorisation. Family: marriage, PACS or birth certificate. "
                 "Visitors: proof of resources and health insurance."},
    ],
}


def rules(h) -> None:
    h.a_date("birth_date", past=True)
    h.match("phone", r"\+33\s?[1-9](?:[\s.]?\d{2}){4}", "Use the French format +33 6 12 34 56 78")
    h.email("email")
    h.match("postcode", r"\d{5}", "A French postcode has 5 digits")
    hosted = h.id("address_proof_type") == "host"
    h.show("host_id_copy", when=hosted)
    h.require("host_id_copy", when=hosted)

    h.a_date("current_visa_expiry", future=True,
             msg="Your visa has expired: you cannot apply online, book an appointment at the prefecture")
    h.a_date("passport_expiry", future=True, msg="Your passport has expired; renew it first")
    h.match("passport_number", r"[A-Za-z0-9]{6,9}", "A passport number has 6 to 9 letters or digits")

    t = h.id("permit_type")
    sections = {
        "student": ("acc_student", ["school_name", "course_name", "course_start", "student_funds",
                                    "enrolment_certificate", "student_funds_proof"]),
        "worker": ("acc_worker", ["employer_name", "employer_siret", "job_title", "contract_type", "monthly_salary",
                                  "work_contract", "work_authorisation"]),
        "family": ("acc_family", ["family_member_name", "family_relation", "family_member_nationality", "family_status_doc"]),
        "visitor": ("acc_visitor", ["visitor_resources", "visitor_resources_proof", "health_insurance_proof", "no_work_pledge"]),
    }
    for key, (acc, names) in sections.items():
        h.show(acc, *names, when=t == key)
        h.require(*names, when=t == key)
    h.set("stamp_fee", str(FEES[t]) if t in FEES else "")

    h.number("student_funds", lo=STUDENT_MIN, msg="Students need at least 615 EUR per month")
    h.number("visitor_resources", lo=VISITOR_MIN, msg="Visitors need at least 1,400 EUR per month")
    h.number("monthly_salary", lo=0, msg="Enter the gross monthly salary")
    h.match("employer_siret", r"\d{14}", "A SIRET has 14 digits (no spaces)")
