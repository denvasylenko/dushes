"""Lab form: an appointment request at a dental practice in Bologna (small; Italian formats, dependent options).

Rules: the codice fiscale has 16 characters (6 letters, 2 digits, a letter, 2 digits, a letter, 3 digits, a letter);
the phone is an Italian +39 number; "pain" reveals a pain level from 1 to 10 and a swelling question;
the dentists offered depend on the reason; the practice is closed on Sundays and on Wednesday afternoons.
"""
from __future__ import annotations

import re

from ..dsl import C, F, opts

FORM_ID = "dental_appointment"

DENTISTS = opts("dr_rossi:Dr. Giulia Rossi (general dentistry)", "dr_bianchi:Dr. Marco Bianchi (emergencies and aesthetics)",
                "dr_ferri:Dr. Paolo Ferri (general dentistry)", "conti:Marta Conti (dental hygienist)")
BY_REASON = {
    "checkup": ["dr_rossi", "dr_ferri"],
    "pain": ["dr_rossi", "dr_bianchi"],
    "cleaning": ["conti", "dr_ferri"],
    "whitening": ["dr_bianchi"],
}

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_patient", "1. Patient",
      C("Accordion", "acc_patient", "About you",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("Input", "codice_fiscale", "Codice fiscale (tax code)", required=True, placeholder="RSSMRA85T10A944S"),
        F("Input", "phone", "Mobile phone", required=True, placeholder="+39 333 123 4567"),
        F("Input", "email", "Email"),
        F("Checkbox", "first_visit", "This is my first visit to the practice"))),
    C("Tab", "tab_visit", "2. Appointment",
      C("Accordion", "acc_reason", "Reason for the visit",
        F("Dropdown", "reason", "Reason", required=True,
          options=opts("checkup:Check-up", "pain:Tooth pain", "cleaning:Professional cleaning", "whitening:Whitening")),
        F("NumberInput", "pain_level", "Pain level (1 = mild, 10 = worst)", required=True),
        F("RadioGroup", "swelling", "Is there any swelling?", required=True, options=opts("yes:Yes", "no:No"))),
      C("Accordion", "acc_slot", "Date and time",
        "Open Monday to Saturday. Closed on Wednesday afternoons and on Sundays.",
        F("Dropdown", "dentist", "Dentist", required=True, options=DENTISTS),
        F("DatePicker", "visit_date", "Preferred date", required=True),
        F("RadioGroup", "visit_time", "Preferred time", required=True,
          options=opts("morning:Morning (9:00-13:00)", "afternoon:Afternoon (14:30-19:00)")),
        F("TextArea", "notes", "Anything we should know?"))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Dental appointment request",
    "starters": ["I have a toothache, can I come tomorrow?", "Book a cleaning", "Are you open on Wednesday afternoon?"],
    "persona": "You are the booking assistant of Studio Dentistico Portico in Bologna. Be friendly and brief; never give "
               "medical advice. For severe pain with swelling, suggest calling the practice.",
    "flow_hints": [
        "Ask the reason first: it decides which dentists are offered.",
        "Tooth pain asks for a pain level from 1 to 10 and whether there is swelling.",
        "Cleaning is done by the hygienist Marta Conti or Dr. Ferri; whitening only by Dr. Bianchi.",
        "The practice is closed on Sundays and on Wednesday afternoons.",
    ],
    "glossary": {
        "codice_fiscale": "The Italian tax code: 16 characters, for example RSSMRA85T10A944S.",
        "phone": "An Italian number starting with +39.",
        "reason": "Check-up 60 EUR, tooth pain visit 70 EUR, professional cleaning 80 EUR, whitening 250 EUR.",
        "first_visit": "A first visit includes a free panoramic X-ray when the dentist needs one.",
        "visit_date": "Open Monday to Saturday; closed on Wednesday afternoons and on Sundays.",
    },
    "pii": ["codice_fiscale", "phone", "email"],
}

PAGE = {
    "path": "/lab/dental",
    "title": "Studio Dentistico Portico, Bologna: book a visit",
    "description": "Appointment request form of Studio Dentistico Portico, a dental practice in Bologna.",
    "keywords": ["dentist", "dental", "tooth", "teeth", "cleaning", "whitening", "bologna"],
    "sections": [
        {"id": "hours", "title": "Opening hours",
         "text": "Monday to Saturday, mornings 9:00 to 13:00 and afternoons 14:30 to 19:00. "
                 "Wednesday: mornings only. Closed on Sunday."},
        {"id": "prices", "title": "Prices",
         "text": "Check-up 60 EUR. Tooth pain visit 70 EUR. Professional cleaning 80 EUR. Whitening 250 EUR. "
                 "A first visit includes a free panoramic X-ray when the dentist needs one."},
        {"id": "team", "title": "Our team",
         "text": "Dr. Giulia Rossi and Dr. Paolo Ferri (general dentistry), Dr. Marco Bianchi (emergencies and aesthetics, "
                 "the only one doing whitening), Marta Conti (dental hygienist, cleanings)."},
    ],
}


def rules(h) -> None:
    cf = h.text("codice_fiscale").upper()
    if cf and not re.fullmatch(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", cf):
        h.error("codice_fiscale", "A codice fiscale has 16 characters, like RSSMRA85T10A944S")
    ph = re.sub(r"[\s\-().]", "", h.text("phone"))
    if ph and not re.fullmatch(r"\+39\d{8,11}", ph):
        h.error("phone", "Enter an Italian number starting with +39, like +39 333 123 4567")
    h.email("email")

    reason = h.id("reason")
    pain = reason == "pain"
    h.show("pain_level", "swelling", when=pain)
    h.require("pain_level", "swelling", when=pain)
    if pain:
        h.number("pain_level", 1, 10, "Enter a pain level from 1 to 10", integer=True)
    if reason in BY_REASON:
        h.options("dentist", [o for o in DENTISTS if o["id"] in BY_REASON[reason]])

    d = h.date("visit_date")
    h.a_date("visit_date", future=True)
    if d and d.weekday() == 6:
        h.error("visit_date", "The practice is closed on Sundays: pick another day")
    if d and d.weekday() == 2 and h.id("visit_time") == "afternoon":
        h.error("visit_time", "On Wednesdays we are open only in the morning")
