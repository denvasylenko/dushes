"""Lab form: a car rental booking (date-time ranges, age-dependent options and fees, a one-way fee, no card fields).

Rules: the pick-up date is today or later; the return (date and time) must be after the pick-up and at most
30 days later; the rental days (started 24 hours) are computed read-only; a different return location shows the
return location (which must differ from the pick-up one) and a read-only one-way fee of 50 EUR; drivers under 21
cannot rent (an error); drivers 21 to 24 pay a young-driver surcharge of 15 EUR a day (read-only, total for the
rental); the premium class is offered only to drivers aged 25 or more; the child seat extra shows the child's age
(0 to 12); payment is at the desk, so the form has no card fields.
"""
from __future__ import annotations

from datetime import date, datetime

from ..dsl import C, F, opts

FORM_ID = "car_rental"

ONE_WAY_FEE = 50
YOUNG_FEE = 15
MAX_DAYS = 30
TIMES = opts(*[f"{t:02d}h:{t:02d}:00" for t in range(8, 21)])
LOCATIONS = opts("airport:Airport terminal", "central:Central station", "harbour:Harbour office")
CLASSES = opts("economy:Economy (35 EUR a day)", "compact:Compact (45 EUR a day)", "suv:SUV (70 EUR a day)",
               "premium:Premium (110 EUR a day, 25+ only)")

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_trip", "Trip",
      C("Accordion", "acc_pickup", "Pick-up and return",
        "Open every day 08:00 to 20:00. Rentals up to 30 days.",
        F("Dropdown", "pickup_location", "Pick-up location", required=True, options=LOCATIONS),
        F("DatePicker", "pickup_date", "Pick-up date", required=True),
        F("Dropdown", "pickup_time", "Pick-up time", required=True, options=TIMES),
        F("DatePicker", "return_date", "Return date", required=True),
        F("Dropdown", "return_time", "Return time", required=True, options=TIMES),
        F("Input", "rental_days", "Rental days (calculated)", readonly=True),
        F("Checkbox", "different_return", "Return the car to a different location (+50 EUR)"),
        F("Dropdown", "return_location", "Return location", required=True, options=LOCATIONS),
        F("Input", "one_way_fee", "One-way fee (EUR, calculated)", readonly=True))),
    C("Tab", "tab_driver", "Driver",
      C("Accordion", "acc_driver", "Main driver",
        "Drivers must be 21 or older. Drivers under 25 pay 15 EUR a day.",
        F("Input", "driver_name", "Full name", required=True),
        F("NumberInput", "driver_age", "Age", required=True),
        F("Input", "licence_number", "Driving licence number", required=True),
        F("NumberInput", "licence_years", "Years holding a licence", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Phone", required=True, placeholder="+351 912 345 678"),
        F("Input", "young_driver_fee", "Young-driver surcharge (EUR, calculated)", readonly=True))),
    C("Tab", "tab_car", "Car and extras",
      C("Accordion", "acc_car", "Car",
        F("RadioGroup", "car_class", "Car class", required=True, options=CLASSES),
        F("MultiSelect", "extras", "Extras",
          options=opts("child_seat:Child seat (5 EUR a day)", "gps:Navigation (4 EUR a day)",
                       "extra_driver:Additional driver (8 EUR a day)", "snow_chains:Snow chains (20 EUR)")),
        F("NumberInput", "child_age", "Child's age (for the right seat)", required=True),
        "Payment is made at the desk when you pick up the car, by card or cash. Nothing is charged now.",
        F("Checkbox", "accept_terms", "I accept the rental terms", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Car rental booking: Sunroad Rentals",
    "starters": ["Rent a car for next week", "I'm 23, can I rent a car?", "Can I return the car at the airport?"],
    "persona": "You are Sunroad Rentals' booking assistant. Be quick and clear; never ask for card details, payment is at the desk.",
    "flow_hints": [
        "Where and when first: the return must be after the pick-up and within 30 days.",
        "A different return location adds a 50 EUR one-way fee.",
        "Drivers under 21 cannot rent; under 25 pay 15 EUR a day; premium cars are 25+ only.",
        "Payment is at the desk: never ask for card details.",
    ],
    "glossary": {
        "driver_age": "21 or older; 21 to 24 pay a young-driver surcharge of 15 EUR a day.",
        "car_class": "Economy 35, compact 45, SUV 70, premium 110 EUR a day; premium only for drivers 25+.",
        "one_way_fee": "50 EUR when the car is returned to a different location.",
        "rental_days": "Every started 24 hours counts as a day; at most 30 days.",
        "extras": "Child seat 5, navigation 4, additional driver 8 EUR a day; snow chains 20 EUR per rental.",
    },
    "pii": ["driver_name", "licence_number", "email", "phone"],
}

PAGE = {
    "path": "/lab/car-rental",
    "title": "Sunroad Rentals: book a car",
    "description": "Sunroad Rentals' car rental booking form, with pick-up at the airport, the central station or the harbour.",
    "keywords": ["car", "rental", "rent a car", "hire", "vehicle", "airport", "driver"],
    "sections": [
        {"id": "prices", "title": "Prices",
         "text": "Economy 35 EUR, compact 45 EUR, SUV 70 EUR and premium 110 EUR a day. "
                 "Returning to a different location costs a one-way fee of 50 EUR. Rentals up to 30 days."},
        {"id": "drivers", "title": "Drivers",
         "text": "Drivers must be at least 21. Drivers under 25 pay a young-driver surcharge of 15 EUR a day "
                 "and cannot rent premium cars."},
        {"id": "payment", "title": "Payment",
         "text": "You pay at the desk when you pick up the car, by card or cash. Nothing is charged online."},
    ],
}


def _at(h, d: str, t: str) -> datetime | None:
    day, tm = h.date(d), h.id(t)
    if day is None or not tm:
        return None
    try:
        hh = int(tm[:2])
        return datetime(day.year, day.month, day.day, hh) if 0 <= hh <= 23 else None
    except ValueError:
        return None


def rules(h) -> None:
    h.a_date("pickup_date", after=date.today(), msg="The pick-up date cannot be in the past")
    start, end = _at(h, "pickup_date", "pickup_time"), _at(h, "return_date", "return_time")
    days = None
    if start and end:
        if end <= start:
            h.error("return_date", "The return must be after the pick-up")
        else:
            hours = (end - start).total_seconds() / 3600
            days = int(-(-hours // 24))
            if days > MAX_DAYS:
                h.error("return_date", "Rentals are at most 30 days: choose an earlier return")
            else:
                h.set("rental_days", days)

    one_way = h.on("different_return")
    h.show("return_location", "one_way_fee", when=one_way)
    h.require("return_location", when=one_way)
    if one_way:
        h.set("one_way_fee", ONE_WAY_FEE)
        if h.id("return_location") and h.id("return_location") == h.id("pickup_location"):
            h.error("return_location", "Choose a location other than the pick-up one, or untick the box")

    h.number("driver_age", 16, 99, msg="Enter the driver's age (16 to 99)", integer=True)
    age = h.num("driver_age")
    if age is not None and not h.has_error("driver_age") and age < 21:
        h.error("driver_age", "Drivers must be at least 21 to rent")
    young = age is not None and 21 <= age < 25
    h.show("young_driver_fee", when=young)
    if young:
        h.set("young_driver_fee", YOUNG_FEE * days if days and days <= MAX_DAYS else YOUNG_FEE)
    h.number("licence_years", 1, 80, msg="You need to have held a licence for at least 1 year")
    h.email("email")
    h.phone("phone")

    allowed = CLASSES if age is None or age >= 25 else [o for o in CLASSES if o["id"] != "premium"]
    h.options("car_class", allowed)
    if h.id("car_class") == "premium" and age is not None and age < 25:
        h.clear("car_class")
    seat = "child_seat" in h.ids("extras")
    h.show("child_age", when=seat)
    h.require("child_age", when=seat)
    h.number("child_age", 0, 12, msg="Child seats are for children aged 0 to 12", integer=True)
