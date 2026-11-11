"""Demo form 2: barbershop booking (English labels).

A completely different domain from the loan form, to show the agent core is
form-agnostic. Also shows the "inline" domain-pack channel: the form backend
ships the pack (DOMAIN) together with the JSX.
"""
from __future__ import annotations

import copy
import hashlib
import re
from datetime import date
from typing import Any

from .dsl import C, F, base_props, initial_state, opts, to_jsx

SERVICES = opts("haircut:Haircut", "beard:Beard trim", "combo:Haircut + beard", "kids:Kids haircut")
SERVICE_BASE = {"haircut": (30, 40), "beard": (20, 25), "combo": (50, 60), "kids": (25, 25)}  # minutes, $
BARBERS = {
    "haircut": ["alex", "ivan", "maria"],
    "beard": ["ivan", "omar"],
    "combo": ["ivan"],
    "kids": ["maria"],
}
BARBER_NAMES = {"alex": "Alex", "ivan": "Ivan", "maria": "Maria (senior)", "omar": "Omar"}
HOURS = [f"{h:02d}:00" for h in range(10, 19)]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "step_service", "1. Service",
      C("Accordion", "acc_service", "Choose a service",
        F("Dropdown", "service", "Service", required=True, options=SERVICES),
        F("NumberInput", "child_age", "Child's age", required=True),
        F("Dropdown", "barber", "Barber", required=True, options=[]),
        F("Checkbox", "add_wash", "Add hair wash (+$10, +15 min)"),
        F("Checkbox", "add_styling", "Add styling (+$15, +10 min)"),
        F("Input", "duration", "Duration, min (calculated)", readonly=True),
        F("Input", "price", "Price, $ (calculated)", readonly=True))),
    C("Tab", "step_time", "2. Date & time",
      C("Accordion", "acc_slot", "Pick a time slot",
        "Times are shown in the salon's local time. We are closed on Sundays.",
        F("DatePicker", "visit_date", "Date", required=True),
        F("Dropdown", "time_slot", "Time", required=True, options=[]))),
    C("Tab", "step_contacts", "3. Your details",
      C("Accordion", "acc_contact", "Contact details",
        F("Input", "client_name", "Name", required=True),
        F("Input", "client_phone", "Phone", required=True, placeholder="+1 555 123 4567"),
        F("Input", "client_email", "Email"),
        F("Checkbox", "first_visit", "This is my first visit"),
        F("Input", "comment", "Comment for the barber")),
      C("Accordion", "acc_reminders", "Reminders",
        F("Checkbox", "remind", "Send me a reminder"),
        F("Dropdown", "remind_channel", "Channel", required=True,
          options=opts("sms:SMS", "email:Email", "whatsapp:WhatsApp")),
        F("Dropdown", "remind_before", "When", required=True,
          options=opts("2h:2 hours before", "1d:1 day before")))),
    C("Tab", "step_confirm", "4. Confirm",
      C("Accordion", "acc_confirm", "Review and confirm",
        F("Input", "summary", "Booking summary", readonly=True),
        F("Checkbox", "agree_policy", "I agree to the cancellation policy (free up to 2 hours before)",
          required=True))),
)

FORM_JSX = to_jsx(FORM)
BASE_PROPS = base_props(FORM)
INITIAL_STATE = initial_state(FORM)

# Shipped by the form backend next to the JSX (inline domain pack).
DOMAIN = {
    "form_id": "barber_booking",
    "title": "Barbershop booking",
    "starters": ["Book me a haircut + beard next Tuesday around 3pm", "How much is a haircut with Maria?",
                 "Book a kids haircut for my son, he is 6"],
    "persona": "You are the barbershop's friendly booking assistant. Keep it short and casual.",
    "flow_hints": [
        "Choose the service first: the list of barbers depends on it.",
        "Available times depend on both the date and the barber.",
        "The steps unlock one by one: service → date & time → your details → confirm.",
    ],
    "glossary": {
        "barber": "Maria is a senior barber: her prices are 20% higher. Kids haircuts are done only by Maria.",
        "agree_policy": "Cancellation is free up to 2 hours before the visit; later cancellations cost 50%.",
        "first_visit": "First-time clients get 10% off; the discount is applied at the salon, not in the price shown.",
    },
    "pii": ["client_phone", "client_email"],
}


def _id(v: Any) -> str | None:
    return v.get("id") if isinstance(v, dict) else None


def _slots(day: date, barber: str) -> list[dict[str, str]]:
    """Free slots: deterministic pseudo-random "booked" hours per barber and day."""
    if day.weekday() == 6:
        return []
    seed = int(hashlib.md5(f"{day}{barber}".encode()).hexdigest(), 16)
    booked = {HOURS[seed % len(HOURS)], HOURS[(seed // 7) % len(HOURS)], HOURS[(seed // 13) % len(HOURS)]}
    return [{"id": h, "name": h} for h in HOURS if h not in booked]


def compute_config(state: dict[str, Any] | None = None) -> dict[str, Any]:
    st = {**INITIAL_STATE, **(state or {})}
    pr = copy.deepcopy(BASE_PROPS)

    def filled(*names: str) -> bool:
        return all(st.get(n) not in (None, "", False) for n in names)

    service, barber = _id(st.get("service")), _id(st.get("barber"))
    pr["barber"]["options"] = [{"id": b, "name": BARBER_NAMES[b]} for b in BARBERS.get(service or "", [])]
    pr["barber"]["disabled"] = service is None
    pr["child_age"]["visible"] = service == "kids"
    if service == "kids" and str(st.get("child_age") or "").strip():
        try:
            age = int(str(st["child_age"]).strip())
            if not 1 <= age <= 14:
                pr["child_age"]["error"] = "Kids haircut is for ages 1–14"
        except ValueError:
            pr["child_age"]["error"] = "Enter a number"

    # price and duration (read-only)
    if service:
        minutes, price = SERVICE_BASE[service]
        if st.get("add_wash"):
            minutes, price = minutes + 15, price + 10
        if st.get("add_styling"):
            minutes, price = minutes + 10, price + 15
        if barber == "maria":
            price = round(price * 1.2)
        st["duration"], st["price"] = str(minutes), str(price)
    else:
        st["duration"] = st["price"] = ""

    # date & time
    day = None
    try:
        day = date.fromisoformat(str(st.get("visit_date") or ""))
    except ValueError:
        pass
    if day and day < date.today():
        pr["visit_date"]["error"] = "This date is in the past"
    elif day and day.weekday() == 6:
        pr["visit_date"]["error"] = "We are closed on Sundays"
    slots = _slots(day, barber) if day and barber and day >= date.today() else []
    pr["time_slot"]["options"] = slots
    pr["time_slot"]["disabled"] = not (day and barber)

    # contacts and reminders
    phone = str(st.get("client_phone") or "").strip()
    if phone and not re.fullmatch(r"\+?\d[\d\s\-()]{7,}", phone):
        pr["client_phone"]["error"] = "Enter a valid phone number"
    remind = bool(st.get("remind"))
    pr["remind_channel"]["visible"] = pr["remind_before"]["visible"] = remind
    if remind and _id(st.get("remind_channel")) == "email":
        pr["client_email"]["required"] = True
    email = str(st.get("client_email") or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        pr["client_email"]["error"] = "Enter a valid email"

    # steps unlock one by one
    service_ok = filled("service", "barber") and (service != "kids" or filled("child_age"))
    pr["step_time"]["disabled"] = not service_ok
    slot_ok = service_ok and filled("visit_date", "time_slot") and not pr["visit_date"].get("error")
    pr["step_contacts"]["disabled"] = not slot_ok
    contacts_ok = slot_ok and filled("client_name", "client_phone") and not pr["client_phone"].get("error")
    pr["step_confirm"]["disabled"] = not contacts_ok

    # summary (read-only)
    if contacts_ok:
        svc = next(o["name"] for o in SERVICES if o["id"] == service)
        st["summary"] = (f"{svc} with {BARBER_NAMES.get(barber or '', barber)}, {st['visit_date']} "
                         f"{_id(st.get('time_slot'))}, {st['duration']} min, ${st['price']}")
    else:
        st["summary"] = ""
    return {"props": pr, "state": st}
