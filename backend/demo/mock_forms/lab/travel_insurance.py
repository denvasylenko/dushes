"""Lab form: a single-trip travel insurance quote (medium; dates, a repeating group, a computed premium).

Rules: the return date is after the departure date and the trip is at most 90 days (both days counted);
the departure is not in the past; up to 6 travellers (name, date of birth), and a traveller aged 80 or over on the
departure date is not covered (error); the premium is computed: daily rate of the cover level x days x travellers,
x1.5 with winter sports.
"""
from __future__ import annotations

from ..dsl import C, F, opts

FORM_ID = "travel_insurance"
MAX_TRAVELLERS = 6
RATES = {"basic": 2.00, "standard": 3.50, "premium": 5.50}   # EUR per traveller per day
WINTER = 1.5

TRAVELLERS = [[f"traveller_{i}_name", f"traveller_{i}_birth"] for i in range(1, MAX_TRAVELLERS + 1)]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_trip", "1. Trip",
      C("Accordion", "acc_trip", "Where and when",
        F("MultiSelect", "destinations", "Destination countries", required=True,
          options=opts("fr:France", "es:Spain", "it:Italy", "gr:Greece", "pt:Portugal", "ch:Switzerland", "at:Austria",
                       "gb:United Kingdom", "us:United States", "ca:Canada", "mx:Mexico", "jp:Japan", "th:Thailand",
                       "au:Australia", "ma:Morocco")),
        F("DatePicker", "departure_date", "Departure date", required=True),
        F("DatePicker", "return_date", "Return date", required=True),
        "A trip can last up to 90 days, counting the departure and the return day.")),
    C("Tab", "tab_travellers", "2. Travellers",
      C("Accordion", "acc_travellers", "Who is travelling",
        "Up to 6 travellers per policy. Travellers aged 80 or over cannot be covered.",
        F("NumberInput", "traveller_count", "Number of travellers", required=True),
        *[F(t, n, f"Traveller {i}: {lbl}") for i, grp in enumerate(TRAVELLERS, 1)
          for t, n, lbl in (("Input", grp[0], "full name"), ("DatePicker", grp[1], "date of birth"))])),
    C("Tab", "tab_cover", "3. Cover and price",
      C("Accordion", "acc_cover", "Cover",
        F("RadioGroup", "cover_level", "Cover level", required=True,
          options=opts("basic:Basic (2.00 EUR per traveller per day)", "standard:Standard (3.50 EUR per traveller per day)",
                       "premium:Premium (5.50 EUR per traveller per day)")),
        F("Checkbox", "winter_sports", "Add winter sports (skiing, snowboarding): price x1.5"),
        F("Input", "premium", "Total premium, EUR (calculated)", readonly=True)),
      C("Accordion", "acc_holder", "Policyholder",
        F("Input", "holder_email", "Email for the policy", required=True),
        F("Input", "holder_phone", "Phone"),
        F("Checkbox", "terms", "I have read the policy terms", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Travel insurance quote",
    "starters": ["Insure a family of four for two weeks in Spain", "How much is a ski trip to Austria?",
                 "Can my 82-year-old father be covered?"],
    "persona": "You are the quote assistant of Wayfarer Cover, a travel insurer. Be clear about prices and limits.",
    "flow_hints": [
        "Trip first: countries, departure and return dates (at most 90 days, both days counted).",
        "Then the travellers: set the number (1 to 6), then each name and date of birth.",
        "The premium is calculated by the form; never compute or promise a different price.",
    ],
    "glossary": {
        "cover_level": "Basic 2.00, Standard 3.50, Premium 5.50 EUR per traveller per day.",
        "winter_sports": "Winter sports multiply the whole premium by 1.5.",
        "premium": "Daily rate x trip days x travellers, x1.5 with winter sports. Days count the departure and the return day.",
        "traveller_count": "Up to 6 travellers; anyone aged 80 or over on the departure date is not covered.",
    },
    "pii": ["holder_email", "holder_phone", *[n for g in TRAVELLERS for n in g]],
}

PAGE = {
    "path": "/lab/travel-insurance",
    "title": "Wayfarer Cover: travel insurance",
    "description": "Wayfarer Cover's single-trip travel insurance quote form.",
    "keywords": ["travel", "insurance", "trip", "holiday", "ski", "abroad"],
    "sections": [
        {"id": "prices", "title": "How the price is calculated",
         "text": "Daily rate x number of days x number of travellers. Daily rates per traveller: Basic 2.00 EUR, "
                 "Standard 3.50 EUR, Premium 5.50 EUR. Winter sports multiply the total by 1.5. "
                 "Days count both the departure and the return day: 1 to 10 July is 10 days."},
        {"id": "limits", "title": "Limits",
         "text": "Single trips of up to 90 days. Up to 6 travellers per policy. Travellers aged 80 or over on the "
                 "departure date cannot be covered."},
    ],
}


def rules(h) -> None:
    dep, ret = h.date("departure_date"), h.date("return_date")
    h.a_date("departure_date", future=True, msg="The departure date cannot be in the past")
    h.a_date("return_date")
    days = None
    if dep and ret:
        if ret <= dep:
            h.error("return_date", "The return date must be after the departure date")
        else:
            days = (ret - dep).days + 1
            if days > 90:
                h.error("return_date", f"The trip is {days} days; the maximum is 90")

    h.number("traveller_count", 1, MAX_TRAVELLERS, "Enter 1 to 6 travellers", integer=True)
    k = h.repeat("traveller_count", TRAVELLERS, required=("_name", "_birth"))
    for i in range(k):
        b = f"traveller_{i + 1}_birth"
        h.a_date(b, past=True)
        age = h.age(b, on=dep) if dep else h.age(b)
        if age is not None and age >= 80 and not h.has_error(b):
            h.error(b, "Travellers aged 80 or over cannot be covered")

    h.email("holder_email")
    h.phone("holder_phone")

    rate = RATES.get(h.id("cover_level") or "")
    ok = (days is not None and not h.has_error("return_date") and not h.has_error("departure_date")
          and k > 0 and not h.has_error("traveller_count") and rate is not None
          and not any(h.has_error(f"traveller_{i + 1}_birth") for i in range(k)))
    if ok:
        total = rate * days * k * (WINTER if h.on("winter_sports") else 1)
        h.set("premium", f"{total:.2f}")
