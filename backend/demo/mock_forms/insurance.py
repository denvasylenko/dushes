"""Demo form 3: a car insurance application (Harbor Insurance).

The held-out domain of the scenario evals (backend/evals/heldout_*.yaml): its scenarios are run and reported in
their own row, and no prompt rule is tuned on them, so a rule that helps only the bank and the barbershop shows
up as overfitting. Like the barber form, it ships its domain pack next to the JSX.
"""
from __future__ import annotations

import copy
import re
from datetime import date, timedelta
from typing import Any

from .dsl import C, F, base_props, initial_state, opts, to_jsx

MAKES = opts("toyota:Toyota", "volkswagen:Volkswagen", "ford:Ford", "bmw:BMW", "tesla:Tesla")
MODELS = {
    "toyota": opts("corolla:Corolla", "rav4:RAV4", "camry:Camry"),
    "volkswagen": opts("golf:Golf", "passat:Passat", "tiguan:Tiguan"),
    "ford": opts("focus:Focus", "kuga:Kuga", "transit:Transit"),
    "bmw": opts("3series:3 Series", "x3:X3", "x5:X5"),
    "tesla": opts("model3:Model 3", "modely:Model Y"),
}
COVERAGE = opts("liability:Third-party liability", "standard:Standard (liability + theft + fire)",
                "full:Full (everything, including your own damage)")
BASE_PREMIUM = {"liability": 300, "standard": 600, "full": 900}   # euros a year
ACCIDENT_FACTOR = {"0": 1.0, "1": 1.25, "2": 1.6}
DEDUCTIBLE_DISCOUNT = {"250": 0.0, "500": 0.05, "1000": 0.10}

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_vehicle", "1. Vehicle",
      C("Accordion", "acc_vehicle", "Your car",
        F("Dropdown", "make", "Make", required=True, options=MAKES),
        F("Dropdown", "model", "Model", required=True, options=[]),
        F("NumberInput", "year", "Year of manufacture", required=True),
        F("Input", "vin", "VIN (17 characters)", required=True),
        F("Dropdown", "usage", "How the car is used", required=True,
          options=opts("personal:Personal", "commute:Commuting to work", "business:Business")),
        F("NumberInput", "annual_km", "Kilometres a year"))),
    C("Tab", "tab_driver", "2. Driver",
      C("Accordion", "acc_driver", "Main driver",
        F("Input", "driver_name", "Full name", required=True),
        F("DatePicker", "driver_birth", "Date of birth", required=True),
        F("NumberInput", "license_year", "Year the licence was issued", required=True),
        F("Dropdown", "accidents", "At-fault accidents in the last 3 years", required=True,
          options=opts("0:None", "1:One", "2:Two", "3:Three or more")),
        F("Checkbox", "extra_driver", "Someone else will drive the car too")),
      C("Accordion", "acc_extra", "Second driver",
        F("Input", "extra_name", "Second driver's full name", required=True),
        F("DatePicker", "extra_birth", "Second driver's date of birth", required=True))),
    C("Tab", "tab_cover", "3. Cover",
      C("Accordion", "acc_cover", "Your cover",
        F("Dropdown", "coverage", "Cover level", required=True, options=COVERAGE),
        F("Dropdown", "deductible", "Deductible (you pay this much of each claim)", required=True,
          options=opts("250:250 €", "500:500 €", "1000:1000 €")),
        F("Checkbox", "roadside", "Roadside assistance (+40 € a year)"),
        F("DatePicker", "start_date", "Cover starts on", required=True),
        F("Input", "premium", "Yearly premium, € (calculated)", readonly=True))),
    C("Tab", "tab_contact", "4. Contact and consent",
      C("Accordion", "acc_contact", "How we reach you",
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Phone", required=True),
        F("Checkbox", "consent_terms", "I have read the policy terms and the information about my data", required=True))),
)

FORM_JSX = to_jsx(FORM)
BASE_PROPS = base_props(FORM)
INITIAL_STATE = initial_state(FORM)

DOMAIN = {
    "form_id": "car_insurance",
    "title": "Car insurance application",
    "starters": ["Insure my 2019 Toyota Corolla", "What does full cover include?", "How is my premium calculated?"],
    "persona": "You are Harbor Insurance's application assistant. Be clear and calm; insurance terms are confusing.",
    "flow_hints": [
        "The vehicle comes first: the models depend on the make, and the cover levels depend on the car's age.",
        "The steps unlock one by one: vehicle, driver, cover, contact and consent.",
        "The premium is calculated by the form once the cover is chosen: read it, never estimate it.",
    ],
    "glossary": {
        "coverage": "Full cover is offered only for cars at most 10 years old.",
        "deductible": "A higher deductible lowers the premium: 500 € takes 5% off, 1000 € takes 10% off. "
                      "Third-party liability has no deductible.",
        "driver_birth": "Drivers under 21 pay 40% more.",
        "accidents": "With three or more at-fault accidents the application cannot be completed online.",
        "roadside": "Included for free with a Tesla.",
        "vin": "17 characters, letters and digits, never the letters I, O or Q; it is on the registration certificate.",
    },
    "pii": ["vin", "email", "phone"],
}


def _id(v: Any) -> str | None:
    return v.get("id") if isinstance(v, dict) else None


def _date(v: Any) -> date | None:
    try:
        return date.fromisoformat(str(v or ""))
    except ValueError:
        return None


def _age(born: date, on: date) -> int:
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def compute_config(state: dict[str, Any] | None = None) -> dict[str, Any]:
    st = {**INITIAL_STATE, **(state or {})}
    pr = copy.deepcopy(BASE_PROPS)
    today = date.today()

    def filled(*names: str) -> bool:
        return all(st.get(n) not in (None, "", False) for n in names)

    # vehicle
    make = _id(st.get("make"))
    pr["model"]["options"] = MODELS.get(make or "", [])
    pr["model"]["disabled"] = make is None
    car_year = None
    if str(st.get("year") or "").strip():
        try:
            car_year = int(str(st["year"]).strip())
            if not 1990 <= car_year <= today.year + 1:
                pr["year"]["error"] = f"Enter a year between 1990 and {today.year + 1}"
        except ValueError:
            pr["year"]["error"] = "Enter a year"
    vin = str(st.get("vin") or "").strip().upper()
    if vin and not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        pr["vin"]["error"] = "A VIN has 17 letters and digits, without I, O or Q"
    vehicle_ok = filled("make", "model", "year", "vin", "usage") and not pr["year"].get("error") and not pr["vin"].get("error")

    # driver
    pr["tab_driver"]["disabled"] = not vehicle_ok
    born = _date(st.get("driver_birth"))
    age = _age(born, today) if born else None
    if age is not None and age < 18:
        pr["driver_birth"]["error"] = "The main driver must be at least 18"
    if born and str(st.get("license_year") or "").strip():
        try:
            ly = int(str(st["license_year"]).strip())
            if ly < born.year + 17 or ly > today.year:
                pr["license_year"]["error"] = "This year does not fit the driver's age"
        except ValueError:
            pr["license_year"]["error"] = "Enter a year"
    if _id(st.get("accidents")) == "3":
        pr["accidents"]["error"] = "With three or more accidents we cannot finish the application online: please call us"
    pr["acc_extra"]["visible"] = bool(st.get("extra_driver"))
    driver_ok = (vehicle_ok and filled("driver_name", "driver_birth", "license_year", "accidents")
                 and not any(pr[n].get("error") for n in ("driver_birth", "license_year", "accidents"))
                 and (not st.get("extra_driver") or filled("extra_name", "extra_birth")))

    # cover
    pr["tab_cover"]["disabled"] = not driver_ok
    old_car = car_year is not None and today.year - car_year > 10
    pr["coverage"]["options"] = [o for o in COVERAGE if not (old_car and o["id"] == "full")]
    cover = _id(st.get("coverage"))
    if cover == "full" and old_car:
        pr["coverage"]["error"] = "Full cover is only for cars up to 10 years old"
    pr["deductible"]["visible"] = cover != "liability"
    if make == "tesla":
        st["roadside"], pr["roadside"]["readonly"] = True, True
    start = _date(st.get("start_date"))
    if start and not today <= start <= today + timedelta(days=60):
        pr["start_date"]["error"] = "Cover can start today or within the next 60 days"
    ded = _id(st.get("deductible")) or "250"
    if cover and not pr["coverage"].get("error") and driver_ok:
        p = BASE_PREMIUM[cover] * ACCIDENT_FACTOR.get(_id(st.get("accidents")) or "0", 1.0)
        young = [a for a in [age, _age(_date(st.get("extra_birth")), today) if _date(st.get("extra_birth")) else None]
                 if a is not None and a < 21]
        if young:
            p *= 1.4
        if _id(st.get("usage")) == "business":
            p *= 1.2
        if cover != "liability":
            p *= 1 - DEDUCTIBLE_DISCOUNT.get(ded, 0.0)
        if st.get("roadside") and make != "tesla":
            p += 40
        st["premium"] = str(round(p))
    else:
        st["premium"] = ""
    cover_ok = (driver_ok and filled("coverage", "start_date") and not pr["coverage"].get("error")
                and not pr["start_date"].get("error") and (cover == "liability" or filled("deductible")))

    # contact and consent
    pr["tab_contact"]["disabled"] = not cover_ok
    email = str(st.get("email") or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        pr["email"]["error"] = "Enter a valid email"
    phone = str(st.get("phone") or "").strip()
    if phone and not re.fullmatch(r"\+?\d[\d\s\-()]{7,}", phone):
        pr["phone"]["error"] = "Enter a valid phone number"
    return {"props": pr, "state": st}
