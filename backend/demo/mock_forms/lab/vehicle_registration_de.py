"""Lab form: registering a vehicle at a (fictional) German district office, with English labels and German
formats (5-digit postcodes, +49 phones, plates like "LD-AB 1234", eVB numbers, a German IBAN for SEPA).

Rules: the tabs unlock one by one (owner, vehicle, insurance and tax). The owner is 18 or older; the postcode has
5 digits. The vehicle type changes the fields: a car asks engine size, power, fuel and CO2; a motorbike asks engine
size and power and offers a seasonal plate (with its first and last month); a trailer asks its permissible total
weight and whether it is braked. The VIN has 17 characters (no I, O or Q); the first registration date is not in the
future. A requested plate follows "district code (1-3 letters) - 1-2 letters, space, 1-4 digits", e.g. "LD-AB 1234".
The eVB number has 7 letters or digits. Vehicle tax is paid by SEPA direct debit: a valid German (DE) IBAN, the
account holder and the mandate are required.
"""
from __future__ import annotations

import re

from ..dsl import C, F, opts

FORM_ID = "vehicle_registration_de"
SEQUENTIAL = True

MONTHS = opts(*[f"{i:02d}:{m}" for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
     "November", "December"], 1)])

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_owner", "1. Owner",
      C("Accordion", "acc_owner", "Registered keeper",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "street", "Street", required=True),
        F("Input", "house_number", "House number", required=True),
        F("Input", "postcode", "Postcode", required=True, placeholder="12345"),
        F("Input", "city", "Town", required=True),
        F("Input", "phone", "Phone", placeholder="+49 151 23456789"),
        F("Input", "email", "Email", required=True))),
    C("Tab", "tab_vehicle", "2. Vehicle",
      C("Accordion", "acc_vehicle", "The vehicle",
        F("RadioGroup", "vehicle_type", "Vehicle type", required=True,
          options=opts("car:Car", "motorbike:Motorbike", "trailer:Trailer")),
        F("Input", "vin", "Vehicle identification number (VIN)", required=True),
        F("Input", "make", "Make", required=True),
        F("Input", "model", "Model"),
        F("DatePicker", "first_registration", "Date of first registration", required=True),
        F("NumberInput", "engine_cc", "Engine size (cc)", required=True),
        F("NumberInput", "power_kw", "Power (kW)", required=True),
        F("Dropdown", "fuel", "Fuel", required=True,
          options=opts("petrol:Petrol", "diesel:Diesel", "electric:Electric", "hybrid:Hybrid", "lpg:LPG")),
        F("NumberInput", "co2", "CO2 emissions (g/km)", required=True),
        F("NumberInput", "trailer_weight", "Permissible total weight (kg)", required=True),
        F("Checkbox", "trailer_braked", "The trailer has its own brakes"),
        F("Checkbox", "season_plate", "I want a seasonal plate"),
        F("Dropdown", "season_from", "Season starts in", required=True, options=MONTHS),
        F("Dropdown", "season_to", "Season ends in", required=True, options=MONTHS)),
      C("Accordion", "acc_plate", "Licence plate",
        "A requested plate costs 10.20 EUR extra. Leave it empty for a random plate.",
        F("Input", "plate_wish", "Requested licence plate", placeholder="LD-AB 1234"))),
    C("Tab", "tab_tax", "3. Insurance and tax",
      C("Accordion", "acc_insurance", "Insurance",
        F("Input", "evb_number", "eVB number (electronic insurance confirmation)", required=True, placeholder="A1B2C3D"),
        F("Input", "insurer", "Insurer", required=True)),
      C("Accordion", "acc_sepa", "Vehicle tax: SEPA direct debit",
        "The customs office collects the vehicle tax each year by direct debit from a German account.",
        F("Input", "account_holder", "Account holder", required=True),
        F("Input", "iban", "IBAN", required=True, placeholder="DE89 3704 0044 0532 0130 00"),
        F("Checkbox", "sepa_mandate", "I authorise the SEPA direct debit of the vehicle tax", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Vehicle registration",
    "starters": ["Register my new car", "I bought a used motorbike", "Can I get a seasonal plate?", "What is an eVB?"],
    "persona": "You are the Lindenau District Vehicle Registration Office's assistant. Be precise about formats.",
    "flow_hints": [
        "The tabs unlock one by one: owner, vehicle, insurance and tax.",
        "The vehicle type decides the questions: cars (engine, power, fuel, CO2), motorbikes (engine, power, seasonal plate), trailers (weight, brakes).",
        "A requested plate is optional and costs 10.20 EUR; the district code is LD.",
        "Vehicle tax is paid only by SEPA direct debit from a German (DE) IBAN.",
    ],
    "glossary": {
        "evb_number": "The eVB number is a 7-character code (letters and digits) the insurer gives you to prove cover.",
        "plate_wish": "Format: district code, hyphen, 1-2 letters, space, 1-4 digits, e.g. LD-AB 1234. Costs 10.20 EUR.",
        "vin": "17 characters on the registration papers (field E); the letters I, O and Q are never used.",
        "postcode": "German postcodes have 5 digits.",
        "season_plate": "A seasonal plate is valid only in the chosen months each year (motorbikes).",
    },
    "pii": ["first_name", "last_name", "birth_date", "phone", "email", "iban", "account_holder", "evb_number"],
}

PAGE = {
    "path": "/lab/vehicle-registration-de",
    "title": "Lindenau District Office: register a vehicle",
    "description": "Lindenau District Vehicle Registration Office (Germany): register a car, motorbike or trailer online.",
    "keywords": ["car", "vehicle", "registration", "licence plate", "germany", "motorbike", "trailer", "evb"],
    "sections": [
        {"id": "need", "title": "What you need",
         "text": "Your address in the district (5-digit postcode), the vehicle's VIN, the eVB number from your "
                 "insurer (7 letters or digits) and a German bank account for the vehicle tax."},
        {"id": "fees", "title": "Fees and plates",
         "text": "Registration costs 27.90 EUR. A requested plate costs 10.20 EUR extra; our district code is LD "
                 "(format LD-AB 1234). Seasonal plates are available for motorbikes. You must be 18 or older."},
        {"id": "tax", "title": "Vehicle tax",
         "text": "Vehicle tax is collected once a year by SEPA direct debit from a German (DE) IBAN only."},
    ],
}


def rules(h) -> None:
    age = h.age("birth_date")
    h.a_date("birth_date", past=True)
    if age is not None and not h.has_error("birth_date") and age < 18:
        h.error("birth_date", "The registered keeper must be 18 or older")
    h.match("postcode", r"\d{5}", "A German postcode has 5 digits")
    h.phone("phone")
    h.email("email")

    t = h.id("vehicle_type")
    motor = t in ("car", "motorbike")
    h.show("engine_cc", "power_kw", when=motor)
    h.require("engine_cc", "power_kw", when=motor)
    h.show("fuel", "co2", when=t == "car")
    h.require("fuel", "co2", when=t == "car")
    h.show("trailer_weight", "trailer_braked", when=t == "trailer")
    h.require("trailer_weight", when=t == "trailer")
    h.show("season_plate", when=t == "motorbike")
    season = t == "motorbike" and h.on("season_plate")
    h.show("season_from", "season_to", when=season)
    h.require("season_from", "season_to", when=season)
    if season and h.id("season_from") and h.id("season_from") == h.id("season_to"):
        h.error("season_to", "A season covers at least two months: pick a different end month")
    h.number("engine_cc", 49, 10000, integer=True, msg="Enter the engine size from 49 to 10000 cc")
    h.number("power_kw", 1, 1500, msg="Enter the power from 1 to 1500 kW")
    h.number("co2", 0, 600, integer=True, msg="Enter CO2 from 0 to 600 g/km")
    h.number("trailer_weight", 100, 40000, integer=True, msg="Enter the weight from 100 to 40000 kg")

    vin = h.text("vin").upper().replace(" ", "")
    if vin and not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        h.error("vin", "A VIN has 17 letters or digits, without I, O or Q")
    h.a_date("first_registration", past=True)
    plate = h.text("plate_wish").upper()
    if plate and not re.fullmatch(r"[A-Z]{1,3}-[A-Z]{1,2} [1-9]\d{0,3}", plate):
        h.error("plate_wish", "Use the format LD-AB 1234: district code, hyphen, 1-2 letters, space, 1-4 digits")
    elif plate and not plate.startswith("LD-"):
        h.error("plate_wish", "Plates in this district start with LD- (e.g. LD-AB 1234)")

    if h.text("evb_number") and not re.fullmatch(r"[A-Z0-9]{7}", h.text("evb_number").upper()):
        h.error("evb_number", "An eVB number has exactly 7 letters or digits")
    h.iban("iban")
    if h.text("iban") and not h.has_error("iban") and not h.text("iban").upper().startswith("DE"):
        h.error("iban", "Vehicle tax needs a German account: the IBAN starts with DE")
