"""Lab form: a handyman quote request (dependent options, a fee computed read-only, conditional property fields).

Rules: the sub-type options depend on the repair type ("Other" has no sub-type and needs a description of at
least 20 characters); the "emergency" urgency is offered only for plumbing and electrical and adds a 60 EUR
call-out fee shown read-only (0 EUR otherwise); an emergency visit is the same day, so the preferred dates are
hidden for it; otherwise the first preferred date is required, both are in the future, not on a Sunday, and the
second differs from the first; the lift question appears for an apartment above the ground floor; roof work is
not done on apartments (the building manages the roof).
"""
from __future__ import annotations

from datetime import date

from ..dsl import C, F, opts

FORM_ID = "home_repair_quote"

CALLOUT = 60
SUBTYPES = {
    "plumbing": opts("leak:Leak", "blocked:Blocked drain", "boiler:Boiler or water heater", "tap:Tap or toilet"),
    "electrical": opts("outage:Power out in part of the home", "socket:Socket or switch", "lighting:Lighting",
                       "fuse:Fuse box"),
    "roof": opts("tiles:Loose or broken tiles", "gutter:Gutters", "roof_leak:Roof leak"),
    "painting": opts("interior:Interior walls", "exterior:Exterior", "doors:Doors and window frames"),
}
URGENCY = opts("standard:Standard (within 7 days)", "soon:Soon (within 48 hours)",
               "emergency:Emergency (same day, +60 EUR call-out)")

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_job", "The job",
      C("Accordion", "acc_job", "What needs fixing",
        F("Dropdown", "repair_type", "Type of repair", required=True,
          options=opts("plumbing:Plumbing", "electrical:Electrical", "roof:Roof", "painting:Painting", "other:Other")),
        F("Dropdown", "repair_subtype", "What exactly?", required=True, options=[]),
        F("TextArea", "description", "Describe the problem"),
        F("RadioGroup", "urgency", "How urgent is it?", required=True, options=URGENCY),
        F("Input", "callout_fee", "Call-out fee (EUR, calculated)", readonly=True),
        F("FileUpload", "photos", "Photos of the problem"))),
    C("Tab", "tab_property", "The property",
      C("Accordion", "acc_property", "Where",
        F("Dropdown", "property_type", "Property type", required=True,
          options=opts("house:House", "apartment:Apartment", "office:Office or shop")),
        F("Input", "street", "Street and number", required=True),
        F("Input", "postcode", "Postcode", required=True, placeholder="1012 AB"),
        F("Input", "city", "City", required=True),
        F("NumberInput", "floor", "Floor (0 = ground floor)", required=True),
        F("RadioGroup", "has_lift", "Is there a lift?", required=True, options=opts("yes:Yes", "no:No")),
        F("TextArea", "access_instructions", "Access instructions (door code, parking, key)"))),
    C("Tab", "tab_when", "When and contact",
      C("Accordion", "acc_when", "Preferred dates",
        "We work Monday to Saturday. Emergency visits are the same day, every day.",
        F("DatePicker", "preferred_date_1", "First choice", required=True),
        F("DatePicker", "preferred_date_2", "Second choice"),
        F("Dropdown", "time_slot", "Time of day", required=True,
          options=opts("morning:Morning (8-12)", "afternoon:Afternoon (12-17)", "any:Any time"))),
      C("Accordion", "acc_contact", "Contact",
        F("Input", "name", "Your name", required=True),
        F("Input", "phone", "Phone", required=True, placeholder="+31 6 12345678"),
        F("Input", "email", "Email", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Repair quote request",
    "starters": ["My kitchen pipe is leaking", "I need a painter for two rooms", "Do you do emergency call-outs?"],
    "persona": "You are FixRight Handyman Services' booking assistant. Be practical; give no safety-critical repair advice.",
    "flow_hints": [
        "Ask what needs fixing first: the sub-type options depend on the repair type.",
        "Emergency (same day) is only for plumbing and electrical and costs a 60 EUR call-out fee.",
        "An emergency needs no preferred dates; the other urgencies need a first-choice date (not a Sunday).",
        "Roof work is not done for apartments.",
    ],
    "glossary": {
        "urgency": "Standard: within 7 days. Soon: within 48 hours. Emergency: same day, plumbing and electrical only, +60 EUR call-out.",
        "callout_fee": "60 EUR for an emergency visit, otherwise 0 EUR.",
        "preferred_date_1": "Monday to Saturday; not needed for an emergency.",
    },
    "pii": ["street", "postcode", "phone", "email", "access_instructions"],
}

PAGE = {
    "path": "/lab/handyman",
    "title": "FixRight Handyman Services: get a quote",
    "description": "FixRight Handyman Services' repair quote request form.",
    "keywords": ["handyman", "repair", "plumber", "electrician", "roof", "painting", "quote", "fix"],
    "sections": [
        {"id": "services", "title": "What we do",
         "text": "Plumbing, electrical, roof and painting jobs, plus small other repairs. "
                 "We do not do roof work on apartments: the building manages the roof."},
        {"id": "prices", "title": "Urgency and fees",
         "text": "Standard visits within 7 days and soon visits within 48 hours have no call-out fee. "
                 "Emergency same-day visits are for plumbing and electrical only and add a 60 EUR call-out fee."},
        {"id": "hours", "title": "Hours",
         "text": "Monday to Saturday 8:00 to 17:00. Emergencies every day."},
    ],
}


def rules(h) -> None:
    kind = h.id("repair_type")
    sub = SUBTYPES.get(kind or "", [])
    h.options("repair_subtype", sub)
    h.show("repair_subtype", when=bool(sub))
    h.require("repair_subtype", when=bool(sub))
    other = kind == "other"
    h.require("description", when=other)
    if other:
        h.length("description", 20, msg="Describe the job in at least 20 characters")

    can_rush = kind in ("plumbing", "electrical")
    h.options("urgency", URGENCY if can_rush else [o for o in URGENCY if o["id"] != "emergency"])
    if h.id("urgency") == "emergency" and not can_rush:
        h.clear("urgency")
    emergency = h.id("urgency") == "emergency"
    h.set("callout_fee", CALLOUT if emergency else 0)

    flat = h.id("property_type") == "apartment"
    if kind == "roof" and flat:
        h.error("repair_type", "We do not do roof work on apartments: choose another repair")
    h.match("postcode", r"\d{4}\s?[A-Za-z]{2}", "A postcode looks like 1012 AB")
    h.number("floor", 0, 60, integer=True)
    fl = h.num("floor")
    up = flat and fl is not None and fl >= 1
    h.show("has_lift", when=up)
    h.require("has_lift", when=up)

    h.show("acc_when", "preferred_date_1", "preferred_date_2", "time_slot", when=not emergency)
    h.require("preferred_date_1", "time_slot", when=not emergency)
    if not emergency:
        today = date.today()
        for n in ("preferred_date_1", "preferred_date_2"):
            h.a_date(n, after=today, msg="Choose a date from today on")
            d = h.date(n)
            if d and d.weekday() == 6:
                h.error(n, "We do not work on Sundays: choose Monday to Saturday")
        d1, d2 = h.date("preferred_date_1"), h.date("preferred_date_2")
        if d1 and d2 and d1 == d2:
            h.error("preferred_date_2", "Choose a different second date")
    h.phone("phone")
    h.email("email")
