"""Lab form: pet insurance for a dog, cat or rabbit in the Netherlands (medium; dependent options, age window, price table).

Rules: the breeds depend on the species; the pet is at least 8 weeks and under 9 years old on the cover start date
(error otherwise); the microchip number has exactly 15 digits; "pre-existing conditions: yes" reveals a description
and a notice that they are excluded; the monthly price is read from the species x plan table on the page.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "pet_insurance"

BREEDS = {
    "dog": opts("labrador:Labrador Retriever", "german_shepherd:German Shepherd", "french_bulldog:French Bulldog",
                "beagle:Beagle", "border_collie:Border Collie", "mixed_dog:Mixed breed"),
    "cat": opts("shorthair:Domestic Shorthair", "maine_coon:Maine Coon", "siamese:Siamese", "persian:Persian",
                "mixed_cat:Mixed breed"),
    "rabbit": opts("dutch:Dutch", "lionhead:Lionhead", "mini_lop:Mini Lop", "mixed_rabbit:Mixed breed"),
}
PRICES = {   # EUR per month
    "dog": {"basic": 18, "plus": 29, "complete": 42},
    "cat": {"basic": 12, "plus": 21, "complete": 31},
    "rabbit": {"basic": 8, "plus": 13, "complete": 19},
}

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_pet", "1. Your pet",
      C("Accordion", "acc_pet", "About your pet",
        F("Input", "pet_name", "Pet's name", required=True),
        F("RadioGroup", "species", "Species", required=True, options=opts("dog:Dog", "cat:Cat", "rabbit:Rabbit")),
        F("Dropdown", "breed", "Breed", required=True, options=[]),
        F("DatePicker", "pet_birth", "Pet's date of birth", required=True),
        F("Input", "microchip", "Microchip number (15 digits)", required=True, placeholder="528140000123456"),
        F("RadioGroup", "neutered", "Neutered or spayed?", required=True, options=opts("yes:Yes", "no:No"))),
      C("Accordion", "acc_health", "Health",
        F("RadioGroup", "preexisting", "Any known illness or injury before today?", required=True,
          options=opts("yes:Yes", "no:No")),
        F("TextArea", "preexisting_details", "Describe the condition and when it started", required=True)),
      C("Accordion", "acc_excluded", "Pre-existing conditions are not covered",
        "Conditions that started before the cover start date are excluded from every plan. The rest of the cover still applies.")),
    C("Tab", "tab_plan", "2. Plan",
      C("Accordion", "acc_plan", "Choose a plan",
        F("RadioGroup", "plan", "Plan", required=True,
          options=opts("basic:Basic (accidents only)", "plus:Plus (accidents and illness, 3,000 EUR a year)",
                       "complete:Complete (accidents and illness, 7,500 EUR a year, dental)")),
        F("DatePicker", "start_date", "Cover start date", required=True),
        F("Input", "monthly_price", "Monthly price, EUR (calculated)", readonly=True))),
    C("Tab", "tab_owner", "3. Owner",
      C("Accordion", "acc_owner", "About you",
        F("Input", "owner_name", "Full name", required=True),
        F("Input", "owner_email", "Email", required=True),
        F("Input", "owner_phone", "Phone", placeholder="+31 6 12345678"),
        F("Input", "owner_postcode", "Postcode", required=True, placeholder="1012 AB"),
        F("Checkbox", "terms", "I accept the policy terms", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Pet insurance",
    "starters": ["Insure my 3-year-old Labrador", "How much is cover for a rabbit?", "My cat has asthma, is it covered?"],
    "persona": "You are Tulip Paws Pet Cover's assistant. Be friendly; never give veterinary advice.",
    "flow_hints": [
        "Species first: the breed list depends on it.",
        "The pet must be at least 8 weeks and under 9 years old on the cover start date.",
        "Pre-existing conditions are always excluded; say so plainly when the owner reports one.",
        "The monthly price comes from the table and is calculated by the form.",
    ],
    "glossary": {
        "plan": "Basic: accidents only. Plus: accidents and illness up to 3,000 EUR a year. Complete: up to 7,500 EUR a year, with dental.",
        "monthly_price": "Dog 18 / 29 / 42 EUR, cat 12 / 21 / 31 EUR, rabbit 8 / 13 / 19 EUR a month for Basic / Plus / Complete.",
        "microchip": "The ISO microchip number: exactly 15 digits.",
        "start_date": "Cover can start today or within the next 60 days.",
    },
    "pii": ["owner_name", "owner_email", "owner_phone", "owner_postcode", "microchip"],
}

PAGE = {
    "path": "/lab/pet-insurance",
    "title": "Tulip Paws Pet Cover: insure your pet",
    "description": "Tulip Paws Pet Cover's pet insurance form for dogs, cats and rabbits in the Netherlands.",
    "keywords": ["pet", "dog", "cat", "rabbit", "insurance", "vet"],
    "sections": [
        {"id": "prices", "title": "Monthly prices",
         "text": "Basic / Plus / Complete: dog 18 / 29 / 42 EUR, cat 12 / 21 / 31 EUR, rabbit 8 / 13 / 19 EUR a month."},
        {"id": "who", "title": "Who can be insured",
         "text": "Dogs, cats and rabbits aged at least 8 weeks and under 9 years on the cover start date, with a "
                 "15-digit microchip. Cover can start today or within the next 60 days. Pre-existing conditions are excluded."},
    ],
}


def rules(h) -> None:
    sp = h.id("species")
    h.show("breed", when=sp in BREEDS)
    h.options("breed", BREEDS.get(sp or "", []))

    start = h.date("start_date")
    h.a_date("start_date", future=True, msg="Cover cannot start in the past")
    if start and start > date.today() + timedelta(days=60) and not h.has_error("start_date"):
        h.error("start_date", "Cover can start within the next 60 days")
    h.a_date("pet_birth", past=True)
    b = h.date("pet_birth")
    if b and not h.has_error("pet_birth"):
        on = start or date.today()
        if (on - b).days < 56:
            h.error("pet_birth", "Your pet must be at least 8 weeks old on the start date")
        elif (h.age("pet_birth", on=on) or 0) >= 9:
            h.error("pet_birth", "We insure pets under 9 years old on the start date")

    chip = re.sub(r"\s", "", h.text("microchip"))
    if chip and not re.fullmatch(r"\d{15}", chip):
        h.error("microchip", "A microchip number has exactly 15 digits")

    pre = h.id("preexisting") == "yes"
    h.show("preexisting_details", "acc_excluded", when=pre)
    h.require("preexisting_details", when=pre)

    h.email("owner_email")
    h.phone("owner_phone")
    h.match("owner_postcode", r"\d{4}\s?[A-Za-z]{2}", "A Dutch postcode looks like 1012 AB")

    price = PRICES.get(sp or "", {}).get(h.id("plan") or "")
    if price is not None:
        h.set("monthly_price", f"{price:.2f}")
