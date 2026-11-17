"""Demo form 4: an internal purchase request (Corran Group, a fictional company).

An untrained domain for the owner's demo: nothing in the package's prompts, rules or domain code is written for
it, it is in no scenario set and no benchmark, and nothing is tuned on it. Its policy lives where a real
company's would: in the form's own labels and errors and in the page's text (demo/site.yaml, /procurement).
The QA Lead may write held-out scenarios from this file later; nobody else does.

Rules: the cost centre depends on the department and decides the budget owner (read-only); a known supplier is
picked from a list, a new one needs a tax id, an IBAN and a contact; up to five item rows (a row appears when the
one above has a description), each with quantity, unit price and VAT rate, its line total computed; above 5,000
EUR (excluding VAT) a second approver appears; above 25,000 EUR three quotes must be attached; a declared
conflict of interest needs details; delivery is at least five days ahead.
"""
from __future__ import annotations

import copy
import re
from datetime import date, timedelta
from typing import Any

from .dsl import C, F, base_props, initial_state, opts, to_jsx

MAX_ITEMS = 5
SECOND_APPROVER_FROM = 5000      # EUR, excluding VAT
THREE_QUOTES_FROM = 25000        # EUR, excluding VAT
LEAD_DAYS = 5

DEPARTMENTS = opts("ops:Operations", "it:IT", "marketing:Marketing", "facilities:Facilities")
COST_CENTRES = {
    "ops": opts("CC-1010:CC-1010 Warehouse", "CC-1020:CC-1020 Logistics"),
    "it": opts("CC-2010:CC-2010 IT infrastructure", "CC-2020:CC-2020 Software licences"),
    "marketing": opts("CC-3010:CC-3010 Campaigns", "CC-3020:CC-3020 Events"),
    "facilities": opts("CC-4010:CC-4010 Office maintenance", "CC-4020:CC-4020 Furniture"),
}
BUDGET_OWNERS = {
    "CC-1010": "Dana Whitlock", "CC-1020": "Dana Whitlock",
    "CC-2010": "Priya Raman", "CC-2020": "Tomas Okafor",
    "CC-3010": "Lena Varga", "CC-3020": "Lena Varga",
    "CC-4010": "Marcus Bell", "CC-4020": "Marcus Bell",
}
SUPPLIERS = opts("s-101:Brightdesk Office Supplies", "s-102:Kestrel IT Hardware", "s-103:Fernway Logistics",
                 "s-104:Halcyon Print & Signs", "s-105:Oakline Furniture")
APPROVERS = opts("a-1:Elena Brandt, Finance Director", "a-2:Hugo Marsh, Chief Operating Officer",
                 "a-3:Ines Kowal, Head of Procurement")
VAT_RATES = opts("21:21% (standard)", "9:9% (reduced)", "0:0% (exempt)")
SITES = opts("hq:Head office, 4 Quay Street, Corranport", "wh:Warehouse, Unit 7 Ridge Park, Corranport",
             "other:Another address")


def _row(i: int) -> list:
    return [F("Input", f"item_{i}_description", f"Item {i}: description", required=i == 1),
            F("NumberInput", f"item_{i}_quantity", f"Item {i}: quantity", required=i == 1),
            F("NumberInput", f"item_{i}_unit_price", f"Item {i}: unit price (EUR, excl. VAT)", required=i == 1),
            F("Dropdown", f"item_{i}_vat", f"Item {i}: VAT rate", required=i == 1, options=VAT_RATES),
            F("Input", f"item_{i}_total", f"Item {i}: line total (EUR, excl. VAT, calculated)", readonly=True)]


FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_requester", "1. Requester",
      C("Accordion", "acc_requester", "Who is asking",
        F("Input", "requester_name", "Your full name", required=True),
        F("Input", "requester_email", "Your work email", required=True),
        F("Dropdown", "department", "Department", required=True, options=DEPARTMENTS),
        F("Dropdown", "cost_centre", "Cost centre", required=True, options=[]),
        F("Input", "budget_owner", "Budget owner (set by the cost centre)", readonly=True))),
    C("Tab", "tab_supplier", "2. Supplier",
      C("Accordion", "acc_supplier", "Supplier",
        F("Dropdown", "supplier_kind", "Is the supplier already on our list?", required=True,
          options=opts("known:Yes, a known supplier", "new:No, a new supplier")),
        F("Dropdown", "known_supplier", "Known supplier", required=True, options=SUPPLIERS)),
      C("Accordion", "acc_new_supplier", "New supplier",
        F("Input", "new_supplier_name", "Legal name", required=True),
        F("Input", "new_supplier_tax_id", "Tax id (VAT number)", required=True, placeholder="XX123456789"),
        F("Input", "new_supplier_iban", "Bank account (IBAN)", required=True),
        F("Input", "new_supplier_bank", "Bank name", required=True),
        F("Input", "new_supplier_contact", "Supplier contact email", required=True))),
    C("Tab", "tab_items", "3. Items",
      C("Accordion", "acc_items", "What you are buying",
        *[f for i in range(1, MAX_ITEMS + 1) for f in _row(i)]),
      C("Accordion", "acc_totals", "Totals",
        F("Input", "subtotal", "Subtotal (EUR, excl. VAT, calculated)", readonly=True),
        F("Input", "vat_total", "VAT (EUR, calculated)", readonly=True),
        F("Input", "grand_total", "Total (EUR, incl. VAT, calculated)", readonly=True))),
    C("Tab", "tab_approval", "4. Approval and compliance",
      C("Accordion", "acc_justification", "Why this purchase",
        F("TextArea", "justification", "Business justification", required=True)),
      C("Accordion", "acc_second_approver", "Second approver",
        F("Dropdown", "second_approver", "Second approver", required=True, options=APPROVERS)),
      C("Accordion", "acc_quotes", "Three quotes",
        F("FileUpload", "quote_1", "Quote 1", required=True),
        F("FileUpload", "quote_2", "Quote 2", required=True),
        F("FileUpload", "quote_3", "Quote 3", required=True)),
      C("Accordion", "acc_conflict", "Conflict of interest",
        F("Dropdown", "conflict", "Do you or a close relative have a personal or financial link to this supplier?",
          required=True, options=opts("no:No", "yes:Yes")),
        F("TextArea", "conflict_details", "Describe the link", required=True),
        F("Checkbox", "declaration", "I declare that the information in this request is true and complete",
          required=True))),
    C("Tab", "tab_delivery", "5. Delivery",
      C("Accordion", "acc_delivery", "Where and when",
        F("Dropdown", "delivery_site", "Deliver to", required=True, options=SITES),
        F("Input", "delivery_address", "Delivery address", required=True),
        F("DatePicker", "delivery_date", "Needed by", required=True),
        F("TextArea", "delivery_notes", "Notes for the supplier"))),
)

FORM_JSX = to_jsx(FORM)
BASE_PROPS = base_props(FORM)
INITIAL_STATE = initial_state(FORM)

# The standard way to configure the agent for a form, kept to the QA Lead's condition for a fair exam: who the
# agent is, and which fields are private. No facts, no rules, no starters: they are on the page and in the form,
# where the agent has to find them.
DOMAIN = {
    "form_id": "procurement_request",
    "title": "Purchase request",
    "persona": "You are Corran Group's purchasing assistant. You help staff fill in an internal purchase request.",
    "pii": ["requester_email", "new_supplier_tax_id", "new_supplier_iban", "new_supplier_contact"],
}


def _id(v: Any) -> str | None:
    return v.get("id") if isinstance(v, dict) else None


def _num(v: Any) -> float | None:
    s = str(v if v is not None else "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _date(v: Any) -> date | None:
    try:
        return date.fromisoformat(str(v or ""))
    except ValueError:
        return None


def _money(x: float) -> str:
    return f"{x:,.2f}"


def compute_config(state: dict[str, Any] | None = None) -> dict[str, Any]:
    st = {**INITIAL_STATE, **(state or {})}
    pr = copy.deepcopy(BASE_PROPS)
    today = date.today()

    def filled(*names: str) -> bool:
        return all(st.get(n) not in (None, "", False) for n in names)

    def err(name: str) -> bool:
        return bool(pr[name].get("error"))

    # requester: the cost centre depends on the department and sets the budget owner
    dept = _id(st.get("department"))
    pr["cost_centre"]["options"] = COST_CENTRES.get(dept or "", [])
    pr["cost_centre"]["disabled"] = dept is None
    cc = _id(st.get("cost_centre"))
    if cc and cc not in {o["id"] for o in COST_CENTRES.get(dept or "", [])}:
        pr["cost_centre"]["error"] = "This cost centre does not belong to the department you chose"
    st["budget_owner"] = BUDGET_OWNERS.get(cc or "", "") if not err("cost_centre") else ""
    email = str(st.get("requester_email") or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@corran\.example", email):
        pr["requester_email"]["error"] = "Use your work email, ending in @corran.example"
    requester_ok = filled("requester_name", "requester_email", "department", "cost_centre") and not (
        err("requester_email") or err("cost_centre"))

    # supplier: a known one from the list, or a new one with its details
    pr["tab_supplier"]["disabled"] = not requester_ok
    kind = _id(st.get("supplier_kind"))
    pr["known_supplier"]["visible"] = kind == "known"
    pr["acc_new_supplier"]["visible"] = kind == "new"
    tax = str(st.get("new_supplier_tax_id") or "").strip().upper().replace(" ", "")
    if tax and not re.fullmatch(r"[A-Z]{2}[0-9A-Z]{8,12}", tax):
        pr["new_supplier_tax_id"]["error"] = "A VAT number is two letters and 8 to 12 letters or digits"
    iban = str(st.get("new_supplier_iban") or "").strip().upper().replace(" ", "")
    if iban and not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", iban):
        pr["new_supplier_iban"]["error"] = "An IBAN starts with two letters and two digits"
    contact = str(st.get("new_supplier_contact") or "").strip()
    if contact and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact):
        pr["new_supplier_contact"]["error"] = "Enter a valid email"
    if kind == "known":
        supplier_ok = filled("known_supplier")
    elif kind == "new":
        supplier_ok = filled("new_supplier_name", "new_supplier_tax_id", "new_supplier_iban", "new_supplier_bank",
                             "new_supplier_contact") and not any(
            err(n) for n in ("new_supplier_tax_id", "new_supplier_iban", "new_supplier_contact"))
    else:
        supplier_ok = False
    supplier_ok = requester_ok and supplier_ok

    # items: a row shows once the row above has a description; each line total and the totals are computed
    pr["tab_items"]["disabled"] = not supplier_ok
    subtotal, vat, rows_ok, any_row = 0.0, 0.0, True, False
    for i in range(1, MAX_ITEMS + 1):
        names = [f"item_{i}_{p}" for p in ("description", "quantity", "unit_price", "vat", "total")]
        shown = i == 1 or bool(str(st.get(f"item_{i - 1}_description") or "").strip())
        for n in names:
            pr[n]["visible"] = shown
        if not shown:
            for n in names:
                st[n] = INITIAL_STATE[n]
            continue
        started = any(st.get(n) not in (None, "", False) for n in names[:4])
        for n in names[:4]:
            pr[n]["required"] = started or i == 1
        qty, price = _num(st.get(names[1])), _num(st.get(names[2]))
        if st.get(names[1]) not in (None, "") and (qty is None or qty <= 0 or qty != int(qty)):
            pr[names[1]]["error"] = "A quantity is a whole number above 0"
        if st.get(names[2]) not in (None, "") and (price is None or price <= 0):
            pr[names[2]]["error"] = "A unit price is above 0"
        rate = _id(st.get(names[3]))
        if qty and price and not err(names[1]) and not err(names[2]):
            line = qty * price
            st[names[4]] = _money(line)
            subtotal += line
            vat += line * (int(rate) if rate else 0) / 100
        else:
            st[names[4]] = ""
        if started:
            any_row = True
            rows_ok = rows_ok and filled(*names[:4]) and not (err(names[1]) or err(names[2]))
    st["subtotal"] = _money(subtotal) if any_row else ""
    st["vat_total"] = _money(vat) if any_row else ""
    st["grand_total"] = _money(subtotal + vat) if any_row else ""
    items_ok = supplier_ok and any_row and rows_ok

    # approval: the thresholds are on the total excluding VAT
    pr["tab_approval"]["disabled"] = not items_ok
    second = subtotal > SECOND_APPROVER_FROM
    quotes = subtotal > THREE_QUOTES_FROM
    pr["acc_second_approver"]["visible"] = second
    pr["acc_quotes"]["visible"] = quotes
    if not second:
        st["second_approver"] = None
    if not quotes:
        for n in ("quote_1", "quote_2", "quote_3"):
            st[n] = None
    conflict = _id(st.get("conflict"))
    pr["conflict_details"]["visible"] = conflict == "yes"
    if conflict != "yes":
        st["conflict_details"] = ""
    just = str(st.get("justification") or "").strip()
    if just and len(just) < 20:
        pr["justification"]["error"] = "Say in a sentence or two why the company needs this (at least 20 characters)"
    approval_ok = (items_ok and filled("justification", "conflict", "declaration") and not err("justification")
                   and (not second or filled("second_approver"))
                   and (not quotes or filled("quote_1", "quote_2", "quote_3"))
                   and (conflict != "yes" or filled("conflict_details")))

    # delivery: one of our sites, or another address; at least five days ahead
    pr["tab_delivery"]["disabled"] = not approval_ok
    site = _id(st.get("delivery_site"))
    pr["delivery_address"]["visible"] = site == "other"
    if site != "other":
        st["delivery_address"] = ""
    when = _date(st.get("delivery_date"))
    if st.get("delivery_date") and when is None:
        pr["delivery_date"]["error"] = "Enter a date"
    elif when and when < today + timedelta(days=LEAD_DAYS):
        pr["delivery_date"]["error"] = f"Suppliers need at least {LEAD_DAYS} days: pick {today + timedelta(days=LEAD_DAYS)} or later"
    return {"props": pr, "state": st}
