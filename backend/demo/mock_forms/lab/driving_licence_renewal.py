"""Lab form: a driving licence renewal at the Norland Road Agency (medium).

Licence numbers look like WM123456A1: 2 letters, 6 digits, 1 letter, 1 digit.

Rules: the licence number has that format; renewal opens 6 months before the expiry date (an expired licence can be
renewed too); the photo is required; any "yes" in the medical self-declaration reveals the details box and the
doctor's certificate upload and makes both required; a driver aged 70 or over needs the doctor's certificate anyway;
vision correction (glasses or lenses) is a checkbox; home delivery needs the address (4-digit postcode), office
pickup needs the office. The read-only fee is 30 EUR, plus 10 EUR for express delivery.
"""
from __future__ import annotations

from datetime import date

from ..dsl import C, F, opts

FORM_ID = "driving_licence_renewal"
SEQUENTIAL = False

YES_NO = opts("no:No", "yes:Yes")
MEDICAL = [
    ("med_epilepsy", "Have you had epilepsy or a seizure in the last 5 years?"),
    ("med_diabetes", "Do you treat diabetes with insulin?"),
    ("med_heart", "Do you have a heart condition that has caused fainting or dizziness?"),
    ("med_vision", "Has a doctor found a loss of vision you cannot correct with glasses?"),
    ("med_sleep", "Do you have a sleep disorder (such as sleep apnoea)?"),
    ("med_other", "Any other condition or medicine that may affect your driving?"),
]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_licence", "1. Licence and driver",
      C("Accordion", "acc_licence", "Your current licence",
        "Renewal opens 6 months before the expiry date.",
        F("Input", "licence_number", "Licence number", required=True, placeholder="WM123456A1"),
        F("DatePicker", "licence_expiry", "Expiry date on the licence", required=True),
        F("MultiSelect", "categories", "Categories to renew", required=True,
          options=opts("am:AM (mopeds)", "a:A (motorcycles)", "b:B (cars)", "c:C (lorries)", "d:D (buses)"))),
      C("Accordion", "acc_driver", "Driver",
        F("Input", "surname", "Surname", required=True),
        F("Input", "first_name", "First name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "phone", "Phone", required=True),
        F("Input", "email", "Email"),
        F("FileUpload", "photo", "New photo (35 x 45 mm, plain background)", required=True))),
    C("Tab", "tab_medical", "2. Health",
      C("Accordion", "acc_medical", "Medical self-declaration",
        "Any 'Yes' answer, and every driver aged 70 or over, needs a doctor's certificate.",
        *[F("RadioGroup", n, label, required=True, options=YES_NO) for n, label in MEDICAL],
        F("TextArea", "med_details", "Tell us more about the condition", required=True),
        F("FileUpload", "doctor_certificate", "Doctor's certificate (under 3 months old)", required=True),
        F("Checkbox", "vision_correction", "I need glasses or contact lenses to drive"))),
    C("Tab", "tab_delivery", "3. Delivery",
      C("Accordion", "acc_delivery", "Getting the new licence",
        F("RadioGroup", "delivery_method", "Delivery", required=True,
          options=opts("home:Post to my home", "express:Express post (+10 EUR)", "pickup:Pick up at an office")),
        F("Input", "delivery_street", "Street and number", required=True),
        F("Input", "delivery_postcode", "Postcode (4 digits)", required=True),
        F("Input", "delivery_city", "City", required=True),
        F("Dropdown", "pickup_office", "Office", required=True,
          options=opts("central:Westmere Central", "harbour:Harbour District", "north:Northgate")),
        F("Input", "fee", "Fee, EUR (calculated)", readonly=True),
        F("Checkbox", "declaration", "I declare that my answers are true", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Driving licence renewal",
    "starters": ["Renew my driving licence", "I'm 72, what do I need?", "My licence expired last month"],
    "persona": "You are the Norland Road Agency's renewal assistant. Be clear and brief; never judge someone's fitness to drive.",
    "flow_hints": [
        "Ask every medical question; a single 'Yes' means a doctor's certificate.",
        "Drivers aged 70 or over always upload a doctor's certificate.",
        "Ask the delivery method before the address: office pickup needs no address.",
    ],
    "glossary": {
        "licence_number": "2 letters, 6 digits, 1 letter, 1 digit, e.g. WM123456A1.",
        "licence_expiry": "Renewal opens 6 months before this date; an expired licence can also be renewed.",
        "doctor_certificate": "Required after any 'Yes' in the health section and for drivers aged 70 or over.",
        "fee": "30 EUR; express post adds 10 EUR (40 EUR).",
        "delivery_postcode": "Norland postcodes have 4 digits.",
    },
    "pii": ["licence_number", "surname", "first_name", "birth_date", "phone", "email", "delivery_street"],
}

PAGE = {
    "path": "/lab/norland-licence",
    "title": "Norland Road Agency: renew your driving licence",
    "description": "Renew a Norland driving licence online.",
    "keywords": ["driving licence", "license", "renewal", "road agency", "norland", "driver"],
    "sections": [
        {"id": "rules", "title": "Before you start",
         "text": "Renewal opens 6 months before the expiry date. Drivers aged 70 or over, and anyone answering 'Yes' to a "
                 "health question, upload a doctor's certificate under 3 months old."},
        {"id": "fees", "title": "Fees",
         "text": "The renewal costs 30 EUR. Express post adds 10 EUR. Pickup at an office is free: Westmere Central, "
                 "Harbour District or Northgate, Monday to Friday 9:00 to 16:00."},
    ],
}


def _add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    for day in (d.day, 30, 29, 28):
        try:
            return date(d.year + y, mo + 1, day)
        except ValueError:
            continue
    return d


def rules(h) -> None:
    h.match("licence_number", r"[A-Za-z]{2}\d{6}[A-Za-z]\d", "A licence number looks like WM123456A1")
    exp = h.date("licence_expiry")
    if h.text("licence_expiry") and exp is None:
        h.error("licence_expiry", "Enter a date")
    elif exp and exp > _add_months(date.today(), 6):
        h.error("licence_expiry", "Renewal opens 6 months before the expiry date; come back later")
    h.a_date("birth_date", past=True)
    age = h.age("birth_date")
    if age is not None and age < 17:
        h.error("birth_date", "A driver is at least 17")
    h.phone("phone")
    h.email("email")

    any_yes = any(h.id(n) == "yes" for n, _ in MEDICAL)
    senior = age is not None and age >= 70
    h.show("med_details", when=any_yes)
    h.require("med_details", when=any_yes)
    h.show("doctor_certificate", when=any_yes or senior)
    h.require("doctor_certificate", when=any_yes or senior)

    m = h.id("delivery_method")
    post = m in ("home", "express")
    h.show("delivery_street", "delivery_postcode", "delivery_city", when=post)
    h.require("delivery_street", "delivery_postcode", "delivery_city", when=post)
    h.show("pickup_office", when=m == "pickup")
    h.require("pickup_office", when=m == "pickup")
    h.match("delivery_postcode", r"\d{4}", "A Norland postcode has 4 digits")
    h.set("fee", "40" if m == "express" else "30")
