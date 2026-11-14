"""Lab form: a callback request at a Madrid furniture shop (tiny: name, Spanish phone, time window).

Rules: all three fields are required; the phone must be a Spanish number (nine digits starting with 6, 7, 8 or 9,
optionally prefixed with +34 or 0034). Callbacks happen only Monday to Friday, 9:00 to 18:00 (a page fact; the time
windows only cover those hours).
"""
from __future__ import annotations

import re

from ..dsl import C, F, opts

FORM_ID = "callback_request"

FORM = C(
    "Accordion", "main", "Request a callback",
    "We call back Monday to Friday between 9:00 and 18:00.",
    F("Input", "full_name", "Your name", required=True),
    F("Input", "phone", "Phone number", required=True, placeholder="+34 612 345 678"),
    F("Dropdown", "time_window", "Best time to call", required=True,
      options=opts("w09_11:Weekdays 9:00-11:00", "w11_13:Weekdays 11:00-13:00",
                   "w13_15:Weekdays 13:00-15:00", "w15_18:Weekdays 15:00-18:00")),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Callback request",
    "starters": ["Can someone call me about a sofa?", "Call me back on Saturday", "I'd like a callback"],
    "persona": "You are Taller Alameda Furniture's assistant in Madrid. Be brief and friendly.",
    "flow_hints": [
        "Three fields: name, a Spanish phone number, a time window.",
        "Callbacks are only Monday to Friday, 9:00 to 18:00: no weekends or evenings.",
    ],
    "glossary": {
        "phone": "A Spanish number: nine digits starting with 6, 7, 8 or 9, with or without +34.",
        "time_window": "Callbacks only on weekdays (Monday to Friday) between 9:00 and 18:00.",
    },
    "pii": ["full_name", "phone"],
}

PAGE = {
    "path": "/lab/madrid-furniture-callback",
    "title": "Taller Alameda Furniture: request a callback",
    "description": "Taller Alameda Furniture, a furniture shop in Madrid: ask us to call you back.",
    "keywords": ["furniture", "sofa", "madrid", "callback", "call me", "shop"],
    "sections": [{"id": "callbacks", "title": "Callbacks",
                  "text": "Our team calls back Monday to Friday from 9:00 to 18:00 (Madrid time). We do not call on "
                          "weekends or public holidays. We call Spanish numbers only (+34)."}],
}


def rules(h) -> None:
    v = re.sub(r"[\s\-().]", "", h.text("phone"))
    if v and not re.fullmatch(r"(\+34|0034)?[6789]\d{8}", v):
        h.error("phone", "Enter a Spanish number: 9 digits starting with 6, 7, 8 or 9 (e.g. +34 612 345 678)")
    h.length("full_name", 2, 80)
