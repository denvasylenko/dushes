"""Lab form: a wedding enquiry at a country estate (date rules, counts that must add up, a computed budget).

Rules: the wedding date is in the future, a Friday or a Saturday, between April and October; guests 20 to 180;
adults plus children under 12 must equal the guest total (the error sits on the children count); the children's
menu appears when there are children; the ceremony time appears with the on-site ceremony; the budget estimate is
read-only: 95 EUR per guest + 3500 EUR venue fee + 800 EUR for an on-site ceremony; "No music" cannot be combined
with other music; rooms 0 to 24 (the estate has 24 rooms).
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "wedding_planner"

PER_HEAD = 95
VENUE_FEE = 3500
CEREMONY_FEE = 800
ROOMS = 24

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_couple", "The couple",
      C("Accordion", "acc_couple", "About you",
        F("Input", "partner_1_name", "Partner 1: full name", required=True),
        F("Input", "partner_2_name", "Partner 2: full name", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Phone", required=True, placeholder="+44 7700 900123"))),
    C("Tab", "tab_day", "The day",
      C("Accordion", "acc_date", "Date and guests",
        "Weddings are held on Fridays and Saturdays from April to October, for 20 to 180 guests.",
        F("DatePicker", "wedding_date", "Wedding date", required=True),
        F("NumberInput", "guest_count", "Number of guests", required=True),
        F("Checkbox", "ceremony_on_site", "We want the ceremony on the estate (+800 EUR)"),
        F("Dropdown", "ceremony_time", "Ceremony time", required=True,
          options=opts("1200:12:00", "1400:14:00", "1600:16:00"))),
      C("Accordion", "acc_menu", "Menu",
        F("NumberInput", "adults_count", "Adults (12 and over)", required=True),
        F("Dropdown", "adult_menu", "Adult menu", required=True,
          options=opts("garden:Garden menu (vegetarian)", "classic:Classic menu", "coast:Coast menu (fish)")),
        F("NumberInput", "kids_count", "Children under 12", required=True),
        F("Dropdown", "kids_menu", "Children's menu", required=True,
          options=opts("mini:Mini classic", "pasta:Pasta and fruit")),
        F("TextArea", "dietary_notes", "Allergies and dietary needs"))),
    C("Tab", "tab_extras", "Music and rooms",
      C("Accordion", "acc_extras", "Extras",
        F("MultiSelect", "music", "Music",
          options=opts("quartet:String quartet", "band:Live band", "dj:DJ", "none:No music")),
        F("NumberInput", "rooms", "Guest rooms to reserve (0 to 24)", required=True),
        F("Input", "budget_estimate", "Estimated budget (EUR, calculated)", readonly=True),
        F("TextArea", "wishes", "Anything else we should know?"))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Wedding enquiry at Hollowmere Estate",
    "starters": ["We want to get married at the estate", "Is 14 June free for 120 guests?", "How much would 80 guests cost?"],
    "persona": "You are Hollowmere Estate's wedding coordinator assistant. Be warm; quote only the estate's published prices.",
    "flow_hints": [
        "The date first: Fridays and Saturdays, April to October only.",
        "Guests 20 to 180; adults plus children under 12 must add up to the guest total.",
        "The budget is estimated: 95 EUR per guest + 3500 EUR venue fee, + 800 EUR for an on-site ceremony.",
        "The estate has 24 guest rooms.",
    ],
    "glossary": {
        "wedding_date": "A Friday or a Saturday between April and October.",
        "guest_count": "20 to 180 guests in total, children included.",
        "kids_count": "Children under 12; adults plus children must equal the number of guests.",
        "budget_estimate": "95 EUR per guest + 3500 EUR venue fee, + 800 EUR when the ceremony is on the estate.",
        "rooms": "Up to 24 guest rooms on the estate.",
    },
    "pii": ["partner_1_name", "partner_2_name", "email", "phone"],
}

PAGE = {
    "path": "/lab/estate-weddings",
    "title": "Hollowmere Estate: wedding enquiry",
    "description": "Hollowmere Estate's wedding enquiry form.",
    "keywords": ["wedding", "venue", "estate", "marriage", "ceremony", "reception", "guests"],
    "sections": [
        {"id": "dates", "title": "When",
         "text": "Weddings on Fridays and Saturdays from April to October, for 20 to 180 guests."},
        {"id": "prices", "title": "Prices",
         "text": "95 EUR per guest (menu and drinks), children included, plus a venue fee of 3500 EUR. "
                 "A ceremony on the estate adds 800 EUR. The estate has 24 guest rooms."},
    ],
}


def rules(h) -> None:
    h.email("email")
    h.phone("phone")
    h.a_date("wedding_date", future=True, msg="Choose a date in the future")
    d = h.date("wedding_date")
    if d and not h.has_error("wedding_date"):
        if not 4 <= d.month <= 10:
            h.error("wedding_date", "Weddings are held from April to October")
        elif d.weekday() not in (4, 5):
            h.error("wedding_date", "Weddings are held on Fridays and Saturdays")

    h.number("guest_count", 20, 180, msg="We host 20 to 180 guests", integer=True)
    on_site = h.on("ceremony_on_site")
    h.show("ceremony_time", when=on_site)
    h.require("ceremony_time", when=on_site)

    h.number("adults_count", 0, 180, integer=True)
    h.number("kids_count", 0, 180, integer=True)
    kids = h.num("kids_count")
    h.show("kids_menu", when=kids is not None and kids > 0)
    h.require("kids_menu", when=kids is not None and kids > 0)
    g, a = h.num("guest_count"), h.num("adults_count")
    if g is not None and a is not None and kids is not None and a + kids != g and not h.has_error("kids_count"):
        h.error("kids_count", f"Adults plus children must add up to {int(g)} guests")

    music = h.ids("music")
    if "none" in music and len(music) > 1:
        h.error("music", "'No music' cannot be combined with other music")
    h.number("rooms", 0, ROOMS, msg="The estate has 0 to 24 rooms to reserve", integer=True)

    if g is not None and not h.has_error("guest_count"):
        h.set("budget_estimate", int(PER_HEAD * g + VENUE_FEE + (CEREMONY_FEE if on_site else 0)))
