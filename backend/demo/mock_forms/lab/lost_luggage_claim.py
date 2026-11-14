"""Lab form: a delayed-bag claim at a (fictional) airline (medium: flight and bag formats, an upload, a delivery
address abroad with postcode rules by country, an IBAN for interim expenses).

Rules: the flight number is 2 letters and 1-4 digits (e.g. AV1234); the flight date is not in the future and not
older than 21 days (claims close after 21 days); the bag tag is 2 letters and 6 digits (e.g. AV123456); the contents
description and the baggage receipt (the Property Irregularity Report) are required; the postcode format follows the
delivery country (DE/FR/ES/IT 5 digits, NL "1234 AB", PT "1234-567", GB UK format, US 5 digits or 5+4); ticking the
interim expenses claim reveals the amount (up to 200 EUR: 40 EUR a day for at most 5 days), the IBAN and the account
holder, all required.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "lost_luggage_claim"

POSTCODES = {
    "DE": (r"\d{5}", "5 digits, e.g. 10115"),
    "FR": (r"\d{5}", "5 digits, e.g. 75001"),
    "ES": (r"\d{5}", "5 digits, e.g. 28013"),
    "IT": (r"\d{5}", "5 digits, e.g. 00184"),
    "NL": (r"\d{4} ?[A-Za-z]{2}", "4 digits and 2 letters, e.g. 1012 AB"),
    "PT": (r"\d{4}-\d{3}", "4 digits, hyphen, 3 digits, e.g. 1100-148"),
    "GB": (r"[A-Za-z]{1,2}\d[A-Za-z\d]? ?\d[A-Za-z]{2}", "the UK format, e.g. SW1A 1AA"),
    "US": (r"\d{5}(-\d{4})?", "5 digits or 5+4, e.g. 10001"),
}

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_flight", "1. Flight",
      C("Accordion", "acc_flight", "Your flight",
        "Report a delayed bag within 21 days of your flight.",
        F("Input", "flight_number", "Flight number", required=True, placeholder="AV1234"),
        F("DatePicker", "flight_date", "Flight date", required=True),
        F("Input", "bag_tag", "Bag tag number", required=True, placeholder="AV123456"))),
    C("Tab", "tab_bag", "2. Bag",
      C("Accordion", "acc_bag", "Describe the bag",
        F("Dropdown", "bag_type", "Bag type", required=True,
          options=opts("hard:Hard-shell suitcase", "soft:Soft suitcase", "duffel:Duffel bag", "backpack:Backpack",
                       "sports:Sports equipment", "other:Other")),
        F("Dropdown", "bag_colour", "Colour", required=True,
          options=opts("black:Black", "grey:Grey", "blue:Blue", "red:Red", "green:Green", "brown:Brown",
                       "multi:Multicoloured", "other:Other")),
        F("Input", "bag_brand", "Brand"),
        F("TextArea", "contents", "What is inside? (the main items)", required=True),
        F("FileUpload", "receipt", "Baggage receipt (Property Irregularity Report)", required=True))),
    C("Tab", "tab_delivery", "3. Delivery and payment",
      C("Accordion", "acc_contact", "Where should we deliver the bag?",
        F("Input", "full_name", "Full name", required=True),
        F("Input", "phone", "Phone", required=True),
        F("Input", "email", "Email", required=True),
        F("Dropdown", "country", "Country", required=True,
          options=opts("DE:Germany", "FR:France", "ES:Spain", "IT:Italy", "NL:Netherlands", "PT:Portugal",
                       "GB:United Kingdom", "US:United States")),
        F("Input", "street", "Street and number", required=True),
        F("Input", "postcode", "Postcode", required=True),
        F("Input", "city", "City", required=True)),
      C("Accordion", "acc_expenses", "Interim expenses",
        "While your bag is delayed we refund essentials: up to 40 EUR a day for at most 5 days (200 EUR).",
        F("Checkbox", "claim_expenses", "I want to claim interim expenses"),
        F("NumberInput", "expenses_amount", "Amount spent (EUR)", required=True),
        F("Input", "iban", "IBAN", required=True),
        F("Input", "account_holder", "Account holder", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Delayed baggage claim",
    "starters": ["My suitcase didn't arrive", "My bag is missing since last week", "Can I get money for toiletries?"],
    "persona": "You are Aurora Skyways' baggage assistant. Be calm and reassuring; get the formats right.",
    "flow_hints": [
        "Flight first: number, date (within the last 21 days) and the bag tag from the sticker on the boarding pass.",
        "The baggage receipt (Property Irregularity Report) from the airport desk must be uploaded.",
        "The postcode format depends on the delivery country.",
        "Interim expenses: up to 40 EUR a day for at most 5 days (200 EUR), paid to an IBAN.",
    ],
    "glossary": {
        "flight_number": "2 letters and 1-4 digits, e.g. AV1234.",
        "bag_tag": "The bag tag number: 2 letters and 6 digits, on the sticker attached to the boarding pass.",
        "receipt": "The Property Irregularity Report you got at the airport's baggage desk.",
        "expenses_amount": "Up to 40 EUR a day for at most 5 days: 200 EUR at most.",
    },
    "pii": ["full_name", "phone", "email", "street", "postcode", "city", "iban", "account_holder"],
}

PAGE = {
    "path": "/lab/delayed-baggage",
    "title": "Aurora Skyways: delayed baggage claim",
    "description": "Aurora Skyways, an airline: report a delayed bag and have it delivered to you.",
    "keywords": ["airline", "baggage", "luggage", "suitcase", "lost", "delayed", "flight", "bag"],
    "sections": [
        {"id": "claim", "title": "Delayed bags",
         "text": "Report a delayed bag within 21 days of your flight. You need the bag tag number (2 letters and "
                 "6 digits) and the Property Irregularity Report from the airport's baggage desk. We deliver the bag "
                 "to Germany, France, Spain, Italy, the Netherlands, Portugal, the United Kingdom or the United States."},
        {"id": "expenses", "title": "Interim expenses",
         "text": "We refund essentials while you wait: up to 40 EUR a day for at most 5 days (200 EUR in total), "
                 "paid by bank transfer to your IBAN."},
    ],
}


def rules(h) -> None:
    fn = h.text("flight_number").upper().replace(" ", "")
    if fn and not re.fullmatch(r"[A-Z]{2}\d{1,4}", fn):
        h.error("flight_number", "A flight number is 2 letters and 1-4 digits, e.g. AV1234")
    h.a_date("flight_date", past=True, after=date.today() - timedelta(days=21),
             msg="Enter a date within the last 21 days: claims close 21 days after the flight")
    tag = h.text("bag_tag").upper().replace(" ", "")
    if tag and not re.fullmatch(r"[A-Z]{2}\d{6}", tag):
        h.error("bag_tag", "A bag tag is 2 letters and 6 digits, e.g. AV123456")

    h.phone("phone")
    h.email("email")
    rule = POSTCODES.get(h.id("country") or "")
    if rule:
        h.match("postcode", rule[0], f"Use the postcode format of this country: {rule[1]}")

    on = h.on("claim_expenses")
    h.show("expenses_amount", "iban", "account_holder", when=on)
    h.require("expenses_amount", "iban", "account_holder", when=on)
    h.number("expenses_amount", 0, 200, msg="We refund up to 200 EUR (40 EUR a day for 5 days)")
    h.iban("iban")
