"""Lab form: registration for a 2-day tech conference in Lisbon (medium; a repeating group, a clash, a computed total).

Rules: the speaker ticket reveals the talk title and is for one person; up to 5 attendees (name, email, dietary needs);
two Day 1 morning workshops clash (an error if both are picked); the promo code, when given, must be EARLYBIRD
(15% off the tickets, not the workshops); "invoice needed" reveals the company, VAT id and billing address;
the total is computed: ticket price x attendees + 80 EUR per workshop per attendee, less the promo.
"""
from __future__ import annotations

import re

from ..dsl import C, F, opts

FORM_ID = "conference_registration"
MAX_ATTENDEES = 5
TICKETS = {"standard": 450, "student": 150, "speaker": 0}   # EUR per attendee
WORKSHOP = 80                                                # EUR per workshop per attendee
PROMO, PROMO_OFF = "EARLYBIRD", 0.15
CLASH = ("ws_k8s", "ws_rust")

ATTENDEES = [[f"attendee_{i}_name", f"attendee_{i}_email", f"attendee_{i}_diet"] for i in range(1, MAX_ATTENDEES + 1)]
DIET = opts("none:No special needs", "vegetarian:Vegetarian", "vegan:Vegan", "gluten_free:Gluten-free",
            "halal:Halal", "other:Other (tell us by email)")

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_tickets", "1. Tickets",
      C("Accordion", "acc_ticket", "Ticket",
        F("RadioGroup", "ticket_type", "Ticket type", required=True,
          options=opts("standard:Standard (450 EUR)", "student:Student (150 EUR, bring a student ID)",
                       "speaker:Speaker (free, for accepted speakers)")),
        F("Input", "talk_title", "Title of your accepted talk", required=True),
        F("NumberInput", "attendee_count", "Number of attendees (1 to 5)", required=True)),
      C("Accordion", "acc_attendees", "Attendees",
        *[F(t, n, f"Attendee {i}: {lbl}", **extra) for i, grp in enumerate(ATTENDEES, 1)
          for t, n, lbl, extra in (("Input", grp[0], "full name", {}), ("Input", grp[1], "email", {}),
                                   ("Dropdown", grp[2], "dietary needs", {"options": DIET}))])),
    C("Tab", "tab_workshops", "2. Workshops",
      C("Accordion", "acc_workshops", "Workshops (80 EUR each, per attendee)",
        "Kubernetes from zero and Rust for the web run at the same time: pick one of them.",
        F("MultiSelect", "workshops", "Workshops",
          options=opts("ws_k8s:Kubernetes from zero (Day 1, 9:00-12:00)", "ws_rust:Rust for the web (Day 1, 9:00-12:00)",
                       "ws_llm:Building with language models (Day 1, 14:00-17:00)",
                       "ws_sec:Web security lab (Day 2, 9:00-12:00)",
                       "ws_a11y:Accessibility in practice (Day 2, 14:00-17:00)")))),
    C("Tab", "tab_payment", "3. Payment",
      C("Accordion", "acc_payment", "Price",
        F("Input", "promo_code", "Promo code"),
        F("Input", "total", "Total, EUR incl. VAT (calculated)", readonly=True),
        F("Checkbox", "invoice_needed", "I need an invoice for a company")),
      C("Accordion", "acc_invoice", "Invoice details",
        F("Input", "company", "Company name", required=True),
        F("Input", "vat_id", "EU VAT id", required=True, placeholder="PT123456789"),
        F("TextArea", "billing_address", "Billing address", required=True),
        F("Input", "billing_email", "Email for the invoice", required=True)),
      C("Accordion", "acc_terms", "Terms",
        F("Checkbox", "code_of_conduct", "I agree to the code of conduct", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Conference registration",
    "starters": ["Register three of us from my team", "I am a speaker, how do I register?", "Which workshops clash?"],
    "persona": "You are the registration assistant of Tidewater Dev Summit 2027 in Lisbon. Be quick and friendly.",
    "flow_hints": [
        "Ticket type first; a speaker ticket is for one person and asks for the talk title.",
        "Set the number of attendees (1 to 5), then each name, email and dietary needs.",
        "Kubernetes from zero and Rust for the web clash (Day 1 morning): only one of them.",
        "The total is calculated by the form; the only promo code is EARLYBIRD (15% off tickets).",
    ],
    "glossary": {
        "ticket_type": "Standard 450 EUR, Student 150 EUR (student ID at the door), Speaker free (accepted speakers only).",
        "workshops": "80 EUR per workshop per attendee, for every ticket type.",
        "promo_code": "EARLYBIRD: 15% off the tickets (not the workshops).",
        "total": "Ticket price x attendees + 80 EUR x workshops x attendees, minus the promo. Prices include VAT.",
        "vat_id": "An EU VAT id: country code and 8 to 12 letters or digits, for example PT123456789.",
    },
    "pii": [n for g in ATTENDEES for n in g[:2]] + ["billing_email", "vat_id"],
}

PAGE = {
    "path": "/lab/conference",
    "title": "Tidewater Dev Summit 2027: register",
    "description": "Registration for Tidewater Dev Summit 2027, a 2-day tech conference in Lisbon, 15 and 16 April 2027.",
    "keywords": ["conference", "tech", "tickets", "workshop", "developer", "summit", "lisbon"],
    "sections": [
        {"id": "prices", "title": "Tickets",
         "text": "Standard 450 EUR, Student 150 EUR (bring a student ID), Speaker free for accepted speakers. Up to 5 "
                 "attendees per booking. Workshops 80 EUR each per attendee. Promo code EARLYBIRD: 15% off the tickets. "
                 "Prices include VAT."},
        {"id": "workshops", "title": "Workshops",
         "text": "Day 1: Kubernetes from zero and Rust for the web (both 9:00-12:00, so pick one), Building with language "
                 "models (14:00-17:00). Day 2: Web security lab (9:00-12:00), Accessibility in practice (14:00-17:00)."},
    ],
}


def rules(h) -> None:
    t = h.id("ticket_type")
    speaker = t == "speaker"
    h.show("talk_title", when=speaker)
    h.require("talk_title", when=speaker)
    h.number("attendee_count", 1, MAX_ATTENDEES, "Enter 1 to 5 attendees", integer=True)
    n = h.num("attendee_count")
    if speaker and n is not None and n > 1 and not h.has_error("attendee_count"):
        h.error("attendee_count", "A speaker ticket is for one person; book other attendees separately")
    k = h.repeat("attendee_count", ATTENDEES, required=("_name", "_email"))
    for i in range(k):
        h.email(f"attendee_{i + 1}_email")

    ws = h.ids("workshops")
    if all(c in ws for c in CLASH):
        h.error("workshops", "Kubernetes from zero and Rust for the web run at the same time: keep one")

    code = h.text("promo_code")
    promo = code.upper() == PROMO
    if code and not promo:
        h.error("promo_code", "This promo code is not valid; leave it empty if you have none")

    inv = h.on("invoice_needed")
    h.show("acc_invoice", "company", "vat_id", "billing_address", "billing_email", when=inv)
    h.require("company", "vat_id", "billing_address", "billing_email", when=inv)
    vat = h.text("vat_id").replace(" ", "").upper()
    if vat and inv and not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{8,12}", vat):
        h.error("vat_id", "An EU VAT id is a country code and 8 to 12 characters, like PT123456789")
    h.email("billing_email")

    price = TICKETS.get(t or "")
    if price is not None and k > 0 and not h.has_error("attendee_count"):
        valid_ws = [w for w in ws if w.startswith("ws_")]
        tickets = price * k * (1 - PROMO_OFF if promo else 1)
        h.set("total", f"{tickets + WORKSHOP * len(valid_ws) * k:.2f}")
