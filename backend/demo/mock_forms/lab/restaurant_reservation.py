"""Lab form: a table reservation at a Lisbon seafood restaurant (small, date-dependent options, a computed deposit).

Rules: the party is 1 to 12 people (13 or more: call us); the date is today or later and never a Monday (closed);
the time slots depend on the weekday: dinner every open day, lunch only on Saturday and Sunday; the number of high
chairs (0-4) appears and is required when children are coming; for a party of more than 8 a read-only deposit
notice appears: "Deposit: 10 EUR per person" with the total.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "restaurant_reservation"

LUNCH = opts("l1230:Lunch 12:30", "l1330:Lunch 13:30", "l1430:Lunch 14:30")
DINNER = opts("d1900:Dinner 19:00", "d1930:Dinner 19:30", "d2030:Dinner 20:30", "d2130:Dinner 21:30")

FORM = C(
    "Accordion", "main", "Book a table",
    "Open Tuesday to Sunday. Lunch on weekends only. Closed on Mondays.",
    F("NumberInput", "party_size", "Number of guests", required=True),
    F("DatePicker", "res_date", "Date", required=True),
    F("Dropdown", "time_slot", "Time", required=True, options=LUNCH + DINNER),
    F("Checkbox", "children", "Children are coming"),
    F("NumberInput", "high_chairs", "High chairs needed", required=True),
    F("TextArea", "allergies", "Allergies or dietary needs"),
    F("Input", "deposit", "Deposit", readonly=True),
    F("Input", "guest_name", "Name for the booking", required=True),
    F("Input", "phone", "Phone", required=True, placeholder="+351 912 345 678"),
    F("Input", "email", "Email"),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Table reservation",
    "starters": ["Table for 4 on Saturday at lunch", "Can we book for 15 people?", "Are you open on Monday?"],
    "persona": "You are Casa do Mar Azul's booking assistant in Lisbon. Be warm and quick.",
    "flow_hints": [
        "Ask the party size and the date first: the time slots depend on the weekday.",
        "Closed on Mondays. Lunch (12:30-14:30) only on Saturday and Sunday; dinner (19:00-21:30) Tuesday to Sunday.",
        "Parties of 13 or more must call +351 21 000 4455. Parties of more than 8 pay a 10 EUR per person deposit.",
    ],
    "glossary": {
        "deposit": "Only for parties of more than 8: 10 EUR per person, deducted from the bill.",
        "high_chairs": "We have 4 high chairs.",
        "allergies": "Our kitchen handles shellfish, fish, gluten and nuts; tell us any allergy.",
    },
    "pii": ["guest_name", "phone", "email"],
}

PAGE = {
    "path": "/lab/lisbon-seafood",
    "title": "Casa do Mar Azul: book a table",
    "description": "Casa do Mar Azul, a seafood restaurant in Lisbon: reserve a table online.",
    "keywords": ["restaurant", "seafood", "lisbon", "table", "booking", "reservation", "dinner", "lunch"],
    "sections": [
        {"id": "hours", "title": "Opening hours",
         "text": "Tuesday to Sunday dinner from 19:00 (last booking 21:30). Lunch on Saturday and Sunday only, "
                 "12:30 to 14:30. Closed on Mondays."},
        {"id": "groups", "title": "Groups",
         "text": "We take online bookings for up to 12 guests. For 13 or more, please call us on +351 21 000 4455. "
                 "Parties of more than 8 pay a deposit of 10 EUR per person, deducted from the bill. "
                 "We have 4 high chairs."},
    ],
}


def rules(h) -> None:
    h.number("party_size", 1, 12, integer=True, msg="Enter 1 to 12 guests")
    n = h.num("party_size")
    if n is not None and n > 12:
        h.pr["party_size"]["error"] = "For 13 or more guests please call us on +351 21 000 4455"

    d = h.date("res_date")
    h.a_date("res_date", future=True)
    if d and d.weekday() == 0:
        h.error("res_date", "We are closed on Mondays: pick another day")
    if d and d.weekday() != 0:
        h.options("time_slot", (LUNCH if d.weekday() >= 5 else []) + DINNER)

    h.show("high_chairs", when=h.on("children"))
    h.require("high_chairs", when=h.on("children"))
    h.number("high_chairs", 0, 4, integer=True, msg="We have 4 high chairs: enter 0 to 4")

    big = n is not None and n == int(n) and 8 < n <= 12
    h.show("deposit", when=big)
    if big:
        h.set("deposit", f"Deposit: 10 EUR per person ({int(n) * 10} EUR in total)")

    h.length("guest_name", 2, 80)
    h.phone("phone")
    h.email("email")
