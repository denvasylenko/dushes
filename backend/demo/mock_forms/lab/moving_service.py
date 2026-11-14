"""Lab form: a home move request (two addresses with floors and lifts, a repeating inventory, a computed estimate).

Rules: the lift question appears for a floor above the ground floor at each address; the moving date is at
least 2 days from today; inventory is a repeating group of 1 to 8 lines (item, quantity 1 to 50, fragile);
storage 0 to 12 weeks; the read-only estimate follows the page: 250 EUR base + 30 EUR per floor without a lift
(at each address) + 12 EUR per item piece + 6 EUR extra per fragile piece + 180 EUR for packing, all +25% on a
Saturday or Sunday, then + 40 EUR per storage week. The two addresses cannot be the same.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "moving_service"

BASE, PER_FLOOR, PER_PIECE, PER_FRAGILE, PACKING, PER_WEEK = 250, 30, 12, 6, 180, 40
WEEKEND = 0.25
MAX_LINES = 8


def _address(p: str, title: str) -> list:
    return [F("Input", f"{p}_street", f"{title}: street and number", required=True),
            F("Input", f"{p}_postcode", f"{title}: postcode", required=True, placeholder="10115"),
            F("Input", f"{p}_city", f"{title}: city", required=True),
            F("NumberInput", f"{p}_floor", f"{title}: floor (0 = ground floor)", required=True),
            F("RadioGroup", f"{p}_lift", f"{title}: is there a lift?", required=True, options=opts("yes:Yes", "no:No"))]


def _line(i: int) -> list:
    return [F("Input", f"item_{i}_name", f"Item {i}: what", required=True),
            F("NumberInput", f"item_{i}_quantity", f"Item {i}: how many", required=True),
            F("Checkbox", f"item_{i}_fragile", f"Item {i}: fragile")]


LINE_GROUPS = [[f"item_{i}_name", f"item_{i}_quantity", f"item_{i}_fragile"] for i in range(1, MAX_LINES + 1)]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_route", "From and to",
      C("Accordion", "acc_origin", "Moving from", *_address("origin", "From")),
      C("Accordion", "acc_destination", "Moving to", *_address("destination", "To")),
      C("Accordion", "acc_date", "Date",
        "Moves on Saturday or Sunday cost 25% more.",
        F("DatePicker", "moving_date", "Moving date", required=True))),
    C("Tab", "tab_inventory", "What we move",
      C("Accordion", "acc_inventory", "Inventory",
        "List up to 8 kinds of items, e.g. '3 wardrobes' or '20 boxes'.",
        F("NumberInput", "item_lines", "How many kinds of items? (1 to 8)", required=True),
        *[f for i in range(1, MAX_LINES + 1) for f in _line(i)])),
    C("Tab", "tab_services", "Services and estimate",
      C("Accordion", "acc_services", "Extra services",
        F("Checkbox", "packing_service", "Pack everything for me (+180 EUR)"),
        F("NumberInput", "storage_weeks", "Storage weeks (0 to 12, 40 EUR a week)", required=True),
        F("Input", "estimate", "Estimated price (EUR, calculated)", readonly=True)),
      C("Accordion", "acc_contact", "Contact",
        F("Input", "name", "Your name", required=True),
        F("Input", "phone", "Phone", required=True, placeholder="+49 151 23456789"),
        F("Input", "email", "Email", required=True),
        F("TextArea", "notes", "Anything we should know (parking, narrow stairs)"))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Moving quote: Hearthway Movers",
    "starters": ["I'm moving flats next month", "How much is a move on a Saturday?", "Can you store my furniture?"],
    "persona": "You are Hearthway Movers' booking assistant. Be practical; quote only the published rates.",
    "flow_hints": [
        "Both addresses first, with the floor; a lift question follows for floors above the ground floor.",
        "Then the inventory: up to 8 lines, each with a quantity and a fragile tick.",
        "The estimate is calculated by the form from the published rates; weekend moves cost 25% more.",
    ],
    "glossary": {
        "moving_date": "At least 2 days from today; Saturday and Sunday cost 25% more.",
        "estimate": "250 EUR base + 30 EUR per floor without a lift at each address + 12 EUR per piece + 6 EUR per "
                    "fragile piece + 180 EUR packing; +25% at weekends; then + 40 EUR per storage week.",
        "storage_weeks": "0 to 12 weeks at 40 EUR a week.",
    },
    "pii": ["origin_street", "destination_street", "phone", "email"],
}

PAGE = {
    "path": "/lab/movers",
    "title": "Hearthway Movers: request a move",
    "description": "Hearthway Movers' home moving request form with an instant estimate.",
    "keywords": ["moving", "movers", "removal", "relocation", "move house", "storage", "packing"],
    "sections": [
        {"id": "rates", "title": "Rates",
         "text": "Base price 250 EUR. 30 EUR for every floor without a lift, at each address. 12 EUR per piece "
                 "moved, plus 6 EUR for each fragile piece. Packing service 180 EUR. Moves on Saturday or Sunday "
                 "cost 25% more. Storage 40 EUR a week, up to 12 weeks (not affected by the weekend rate)."},
        {"id": "booking", "title": "Booking",
         "text": "Book at least 2 days ahead. Up to 8 kinds of items per request."},
    ],
}


def rules(h) -> None:
    floors_no_lift = 0
    for p in ("origin", "destination"):
        h.match(f"{p}_postcode", r"\d{5}", "A postcode has 5 digits, like 10115")
        h.number(f"{p}_floor", 0, 40, integer=True)
        fl = h.num(f"{p}_floor")
        up = fl is not None and not h.has_error(f"{p}_floor") and fl >= 1
        h.show(f"{p}_lift", when=up)
        h.require(f"{p}_lift", when=up)
        if up and h.id(f"{p}_lift") == "no":
            floors_no_lift += int(fl)
    same = all(h.text(f"origin_{x}").lower() == h.text(f"destination_{x}").lower() for x in ("street", "postcode", "city"))
    if same and h.text("origin_street"):
        h.error("destination_street", "The destination is the same as the origin")

    h.a_date("moving_date", after=date.today() + timedelta(days=2), msg="Book at least 2 days ahead")
    d = h.date("moving_date")

    h.number("item_lines", 1, MAX_LINES, msg="List 1 to 8 kinds of items", integer=True)
    k = h.repeat("item_lines", LINE_GROUPS, required=("_name", "_quantity"))
    pieces = fragile = 0
    ok = k > 0
    for i in range(1, MAX_LINES + 1):
        h.number(f"item_{i}_quantity", 1, 50, integer=True)
        if i > k:
            continue
        q = h.num(f"item_{i}_quantity")
        if q is None or h.has_error(f"item_{i}_quantity"):
            ok = False
            continue
        pieces += int(q)
        fragile += int(q) if h.on(f"item_{i}_fragile") else 0

    h.number("storage_weeks", 0, 12, msg="Storage is 0 to 12 weeks", integer=True)
    weeks = h.num("storage_weeks")
    if ok and weeks is not None and not h.has_error("storage_weeks"):
        move = BASE + PER_FLOOR * floors_no_lift + PER_PIECE * pieces + PER_FRAGILE * fragile
        move += PACKING if h.on("packing_service") else 0
        if d and d.weekday() >= 5:
            move *= 1 + WEEKEND
        h.set("estimate", round(move + PER_WEEK * int(weeks), 2))
    h.phone("phone")
    h.email("email")
