"""Lab form: a new-patient intake at a family clinic (medium, conditional fields, dates, phone, insurance).

Rules: the guardian section appears for a patient under 18; the insurer number is required with insurance;
the allergy list appears when allergies are ticked; pregnancy is asked only for female patients aged 12 to 55;
the visit date cannot be on a Sunday or in the past. The tabs unlock one by one.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "clinic_intake"
SEQUENTIAL = True

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_patient", "1. Patient",
      C("Accordion", "acc_patient", "About the patient",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("RadioGroup", "sex", "Sex", required=True, options=opts("female:Female", "male:Male", "other:Other / prefer not to say")),
        F("Input", "phone", "Mobile phone", required=True, placeholder="+44 7700 900123"),
        F("Input", "email", "Email")),
      C("Accordion", "acc_guardian", "Parent or guardian",
        "Patients under 18 need a parent or guardian.",
        F("Input", "guardian_name", "Guardian's full name", required=True),
        F("Dropdown", "guardian_relation", "Relationship", required=True,
          options=opts("mother:Mother", "father:Father", "legal:Legal guardian")),
        F("Input", "guardian_phone", "Guardian's phone", required=True))),
    C("Tab", "tab_health", "2. Health",
      C("Accordion", "acc_health", "Medical history",
        F("Checkbox", "has_allergies", "I have allergies"),
        F("TextArea", "allergies", "Which allergies?", required=True),
        F("MultiSelect", "conditions", "Long-term conditions",
          options=opts("diabetes:Diabetes", "asthma:Asthma", "hypertension:High blood pressure",
                       "heart:Heart disease", "none:None of these")),
        F("TextArea", "medications", "Medicines you take regularly"),
        F("RadioGroup", "pregnant", "Are you pregnant?", required=True, options=opts("yes:Yes", "no:No", "unsure:Not sure")),
        F("Dropdown", "smoking", "Smoking", options=opts("never:Never", "former:Former smoker", "current:Smoker")))),
    C("Tab", "tab_visit", "3. Visit and insurance",
      C("Accordion", "acc_visit", "First appointment",
        "The clinic is open Monday to Saturday. Sunday is closed.",
        F("Dropdown", "doctor", "Doctor", required=True,
          options=opts("dr_hale:Dr. Hale (GP)", "dr_okafor:Dr. Okafor (GP)", "dr_lind:Dr. Lind (paediatrics, under 16 only)")),
        F("DatePicker", "visit_date", "Preferred date", required=True),
        F("Dropdown", "visit_time", "Preferred time", required=True,
          options=opts("morning:Morning (8-12)", "afternoon:Afternoon (12-17)", "evening:Evening (17-20)"))),
      C("Accordion", "acc_insurance", "Payment",
        F("RadioGroup", "payment", "How will you pay?", required=True,
          options=opts("insurance:Health insurance", "self:Self-pay (45 GBP per visit)")),
        F("Dropdown", "insurer", "Insurer", required=True,
          options=opts("bupa:Bupa", "axa:AXA Health", "vitality:Vitality", "aviva:Aviva")),
        F("Input", "member_number", "Membership number", required=True),
        F("Checkbox", "consent", "I agree that the clinic stores my medical data for my care", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "New patient registration",
    "starters": ["Register my 8-year-old daughter", "I want to sign up as a new patient", "Do you take Bupa?"],
    "persona": "You are Riverside Family Clinic's registration assistant. Be warm and precise; never give medical advice.",
    "flow_hints": [
        "The patient first; a patient under 18 needs a parent or guardian.",
        "The tabs unlock one by one: patient, health, visit and insurance.",
        "Dr. Lind sees only children under 16.",
    ],
    "glossary": {
        "payment": "Self-pay is 45 GBP per visit, paid at the reception. Insurers accepted: Bupa, AXA Health, Vitality, Aviva.",
        "visit_date": "The clinic is closed on Sundays.",
    },
    "pii": ["phone", "email", "guardian_phone", "member_number"],
}

PAGE = {
    "path": "/lab/clinic",
    "title": "Riverside Family Clinic: register",
    "description": "Riverside Family Clinic's new patient registration form.",
    "keywords": ["clinic", "doctor", "gp", "patient", "register", "medical"],
    "sections": [{"id": "hours", "title": "Opening hours",
                  "text": "Monday to Saturday 8:00 to 20:00, closed on Sunday. Self-pay visits cost 45 GBP. "
                          "We accept Bupa, AXA Health, Vitality and Aviva."}],
}


def rules(h) -> None:
    age = h.age("birth_date")
    h.a_date("birth_date", past=True)
    h.phone("phone")
    h.email("email")
    minor = age is not None and age < 18
    h.show("acc_guardian", "guardian_name", "guardian_relation", "guardian_phone", when=minor)
    h.require("guardian_name", "guardian_relation", "guardian_phone", when=minor)
    h.phone("guardian_phone")

    h.show("allergies", when=h.on("has_allergies"))
    h.require("allergies", when=h.on("has_allergies"))
    if "none" in h.ids("conditions") and len(h.ids("conditions")) > 1:
        h.error("conditions", "'None of these' cannot be combined with a condition")
    fertile = h.id("sex") == "female" and age is not None and 12 <= age <= 55
    h.show("pregnant", when=fertile)
    h.require("pregnant", when=fertile)

    if age is not None and age >= 16:
        h.options("doctor", [o for o in h.pr["doctor"]["options"] if o["id"] != "dr_lind"])
    d = h.date("visit_date")
    h.a_date("visit_date", future=True)
    if d and d.weekday() == 6:
        h.error("visit_date", "The clinic is closed on Sundays")

    ins = h.id("payment") == "insurance"
    h.show("insurer", "member_number", when=ins)
    h.require("insurer", "member_number", when=ins)
    h.match("member_number", r"[A-Za-z0-9\-]{6,14}", "A membership number has 6 to 14 letters or digits")
