"""Mock form backend for the loan form: rebuilds the whole config from the current state.

These rules are the backend's business logic; the agent does not know them.
It only sees the result (a new config) and infers dependencies on its own.
"""
from __future__ import annotations

import copy
import re
from datetime import date
from typing import Any

from .loan_spec import BASE_PROPS, CAR_MODELS, CITIES, INITIAL_STATE, LOAN_PURPOSES, LOAN_RATES, LOAN_TERMS


def _id(v: Any) -> str | None:
    return v.get("id") if isinstance(v, dict) else None


def _num(v: Any) -> float | None:
    try:
        return float(str(v).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _age(iso: Any) -> int | None:
    try:
        d = date.fromisoformat(str(iso))
    except ValueError:
        return None
    t = date.today()
    return t.year - d.year - ((t.month, t.day) < (d.month, d.day))


def compute_config(state: dict[str, Any] | None = None) -> dict[str, Any]:
    st = {**INITIAL_STATE, **(state or {})}
    pr = copy.deepcopy(BASE_PROPS)

    def hide(*names: str, when: bool = True) -> None:
        for n in names:
            pr[n]["visible"] = not when

    def disable(*names: str, when: bool = True) -> None:
        for n in names:
            pr[n]["disabled"] = when

    def require(*names: str, when: bool = True) -> None:
        for n in names:
            pr[n]["required"] = when

    def error(name: str, msg: str) -> None:
        pr[name]["error"] = msg

    # --- age (read-only) + validation
    for p in ("", "spouse_", "cob_"):
        a = _age(st.get(f"{p}birth_date"))
        st[f"{p}age"] = "" if a is None else str(a)
        if p == "" and a is not None and not 18 <= a <= 75:
            error("birth_date", "The applicant must be 18 to 75 years old")

    # --- addresses: city options depend on the region
    for p in ("reg_", "fact_", "col_realty_"):
        pr[f"{p}city"]["options"] = CITIES.get(_id(st.get(f"{p}region")) or "", [])
    same = bool(st.get("fact_same_as_reg"))
    fact_addr = ["fact_region", "fact_city", "fact_street", "fact_house", "fact_flat", "fact_zip"]
    disable(*fact_addr, when=same)
    if same:
        for f in fact_addr:
            st[f] = st.get("reg_" + f[5:])
        pr["fact_city"]["options"] = pr["reg_city"]["options"]
    hide("fact_rent_amount", when=_id(st.get("fact_housing_type")) != "rent")

    # --- family
    hide("acc_spouse", when=_id(st.get("marital_status")) not in ("married", "civil"))
    disable("marriage_contract", when=_id(st.get("marital_status")) != "married")
    kids = int(_id(st.get("children_count")) or 0)
    for i in (1, 2, 3):
        hide(f"child_{i}_birth_date", when=i > kids)
    hide("spouse_income", when=_id(st.get("spouse_employment")) != "employed")

    # --- employment
    emp = _id(st.get("employment_type"))
    hide("acc_employer", when=emp != "employee")
    hide("acc_business", when=emp != "business")
    hide("acc_pension", when=emp != "pensioner")
    hide("acc_income", when=emp is None)
    has_extra = bool(st.get("has_extra_income"))
    disable("extra_income_amount", "extra_income_source", when=not has_extra)
    require("extra_income_amount", "extra_income_source", when=has_extra)
    if emp == "unemployed":
        require("income_main", when=False)

    # --- loan
    lt = _id(st.get("loan_type"))
    pr["loan_purpose"]["options"] = LOAN_PURPOSES.get(lt or "", [])
    pr["loan_term"]["options"] = LOAN_TERMS.get(lt or "", [])
    disable("loan_purpose", "loan_term", when=lt is None)
    st["loan_rate"] = f"{LOAN_RATES[lt]}" if lt else ""
    hide("down_payment", when=lt not in ("mortgage", "auto"))
    hide("acc_refinance", when=lt != "refinance")
    hide("refi_extra_amount", when=not st.get("refi_extra_cash"))

    amount, term = _num(st.get("loan_amount")), _num(_id(st.get("loan_term")))
    down = _num(st.get("down_payment")) or 0 if lt in ("mortgage", "auto") else 0
    if amount and term and lt:
        r = LOAN_RATES[lt] / 100 / 12
        body = max(amount - down, 0)
        st["monthly_payment"] = f"{body * r / (1 - (1 + r) ** -term):,.0f}".replace(",", " ")
    else:
        st["monthly_payment"] = ""
    if amount is not None and amount < 30000:
        error("loan_amount", "The minimum amount is 30,000 ₽")
    if lt == "mortgage" and amount and down < amount * 0.2:
        error("down_payment", "A mortgage needs a down payment of at least 20% of the loan amount")

    insured = bool(st.get("opt_life_insurance"))
    hide("opt_insurance_company", when=not insured)
    payout = _id(st.get("payout_method"))
    hide("payout_account", "payout_bik", when=payout != "account")

    # --- collateral (mortgage / car loan only)
    hide("tab_collateral", when=lt not in ("mortgage", "auto"))
    hide("tab_collateral_realty", when=lt != "mortgage")
    hide("tab_collateral_auto", when=lt != "auto")
    market = _id(st.get("col_realty_market"))
    hide("acc_collateral_developer", when=market != "new")
    hide("acc_collateral_seller", when=market != "secondary")
    pr["col_car_model"]["options"] = CAR_MODELS.get(_id(st.get("col_car_brand")) or "", [])
    disable("col_car_model", when=not _id(st.get("col_car_brand")))
    purpose = _id(st.get("loan_purpose"))
    hide("acc_collateral_dealer", when=purpose != "car_new")
    hide("col_car_mileage", when=purpose == "car_new")

    # --- co-borrower
    cob = bool(st.get("has_coborrower"))
    hide("cob_relation", "acc_cob_person", "acc_cob_passport", "acc_cob_income", when=not cob)

    # --- assets: number of slots
    for count, slot in (("asset_realty_count", "asset_realty_"), ("asset_vehicle_count", "asset_vehicle_"),
                        ("asset_account_count", "asset_account_"), ("liability_count", "liability_")):
        k = int(_id(st.get(count)) or 0)
        for i in (1, 2, 3):
            hide(f"{slot}{i}", when=i > k)
    for i in (1, 2, 3):
        full = _id(st.get(f"asset_realty_{i}_ownership")) == "share"
        hide(f"asset_realty_{i}_share", when=not full)
    total = sum(_num(st.get(f"liability_{i}_monthly")) or 0 for i in (1, 2, 3)
                if i <= int(_id(st.get("liability_count")) or 0))
    st["liabilities_total_monthly"] = f"{total:,.0f}".replace(",", " ") if total else ""
    income = (_num(st.get("income_main")) or 0) + (_num(st.get("extra_income_amount")) or 0 if has_extra else 0)
    mp = _num(str(st.get("monthly_payment")).replace(" ", "")) or 0
    st["pdn_ratio"] = f"{(mp + total) / income * 100:.0f}%" if income else ""

    # --- documents
    require("doc_income", when=(amount or 0) > 3_000_000 or _id(st.get("income_proof_type")) not in (None, "none"))
    hide("doc_collateral", when=lt not in ("mortgage", "auto"))
    hide("doc_marriage", when=_id(st.get("marital_status")) != "married")
    hide("doc_employment", when=emp != "employee")

    # --- steps: "future" tabs stay disabled until the previous steps are done
    def filled(*names: str) -> bool:
        return all(st.get(n) not in (None, "", False) for n in names)

    loan_ready = filled("loan_type", "loan_purpose", "loan_amount", "loan_term")
    disable("tab_collateral", when=not loan_ready)
    docs_ready = filled("last_name", "first_name", "birth_date", "employment_type") and loan_ready
    disable("tab_documents", when=not docs_ready)

    # --- formats
    fmt = {
        "phone_mobile": (r"\+7\d{10}", "Format: +7XXXXXXXXXX"),
        "employer_phone": (r"\+7\d{10}", "Format: +7XXXXXXXXXX"),
        "email": (r"[^@\s]+@[^@\s]+\.[^@\s]+", "Invalid email"),
        "passport_series": (r"\d{4}", "Series: 4 digits"),
        "passport_number": (r"\d{6}", "Number: 6 digits"),
        "passport_dept_code": (r"\d{3}-\d{3}", "Format: 000-000"),
        "inn": (r"\d{12}", "Personal tax ID: 12 digits"),
        "employer_inn": (r"\d{10}", "Company tax ID: 10 digits"),
        "reg_zip": (r"\d{6}", "Postal code: 6 digits"),
        "col_car_vin": (r"[A-HJ-NPR-Z0-9]{17}", "VIN: 17 characters (Latin letters and digits)"),
    }
    for name, (rx, msg) in fmt.items():
        v = str(st.get(name) or "").strip()
        if v and not re.fullmatch(rx, v):
            error(name, msg)

    return {"props": pr, "state": st}
