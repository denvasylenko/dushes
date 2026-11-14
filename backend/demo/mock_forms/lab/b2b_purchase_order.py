"""Lab form: a large B2B purchase order (120+ fields, 10 line items, totals computed read-only, 5 tabs one by one).

Rules: the EU VAT id is two letters and 8 to 12 digits; "same as billing" hides and un-requires the delivery
address; line items are a repeating group of up to 10 (SKU like ABC-12345, quantity a whole number 1 to 10000,
unit price above 0, discount 0 to 30%); each line total, the subtotal, VAT 21% and the total are read-only;
a subtotal under 500 EUR is an error (on the item count, so it blocks the next tab); "Net 30" is offered only for
a subtotal above 5000 EUR; the refund IBAN is checked; the approver must be someone other than the buyer contact
(a different email); the delivery date is at least 3 working days ahead; the VAT id starts with the country of registration.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "b2b_purchase_order"
SEQUENTIAL = True

MAX_ITEMS = 10
VAT = 0.21
MIN_ORDER = 500
NET30_FROM = 5000
COUNTRIES = opts("NL:Netherlands", "BE:Belgium", "DE:Germany", "FR:France", "LU:Luxembourg", "AT:Austria",
                 "ES:Spain", "IT:Italy", "PL:Poland")
UNITS = opts("pcs:Pieces", "box:Boxes", "kg:Kilograms", "m:Metres")
TERMS = opts("prepay:Prepayment (bank transfer)", "card:Company card on order", "net30:Net 30 days")
ITEM_PARTS = ("sku", "description", "quantity", "unit", "unit_price", "discount", "line_total")


def _item(i: int) -> list:
    return [F("Input", f"item_{i}_sku", f"Line {i}: SKU", required=True, placeholder="ABC-12345"),
            F("Input", f"item_{i}_description", f"Line {i}: description", required=True),
            F("NumberInput", f"item_{i}_quantity", f"Line {i}: quantity", required=True),
            F("Dropdown", f"item_{i}_unit", f"Line {i}: unit", required=True, options=UNITS),
            F("NumberInput", f"item_{i}_unit_price", f"Line {i}: unit price (EUR, excl. VAT)", required=True),
            F("NumberInput", f"item_{i}_discount", f"Line {i}: discount (%)"),
            F("Input", f"item_{i}_line_total", f"Line {i}: line total (EUR, calculated)", readonly=True)]


def _address(prefix: str, title: str) -> list:
    return [F("Input", f"{prefix}_attention", f"{title}: attention of", required=True),
            F("Input", f"{prefix}_street", f"{title}: street and number", required=True),
            F("Input", f"{prefix}_street2", f"{title}: building, floor (optional)"),
            F("Input", f"{prefix}_postcode", f"{title}: postcode", required=True),
            F("Input", f"{prefix}_city", f"{title}: city", required=True),
            F("Dropdown", f"{prefix}_country", f"{title}: country", required=True, options=COUNTRIES)]


ITEM_GROUPS = [[f"item_{i}_{p}" for p in ITEM_PARTS] for i in range(1, MAX_ITEMS + 1)]
DELIVERY = [f.name for f in _address("delivery", "Delivery")] + ["delivery_phone"]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_buyer", "1. Buyer",
      C("Accordion", "acc_company", "Company",
        F("Input", "company_name", "Legal company name", required=True),
        F("Input", "trading_name", "Trading name (if different)"),
        F("Input", "registration_number", "Chamber of commerce number", required=True),
        F("Input", "vat_id", "EU VAT id", required=True, placeholder="NL123456789B01"),
        F("Dropdown", "industry", "Industry",
          options=opts("retail:Retail", "manufacturing:Manufacturing", "hospitality:Hospitality",
                       "construction:Construction", "office:Office and services", "other:Other")),
        F("Dropdown", "company_size", "Company size",
          options=opts("1:1 to 9 staff", "10:10 to 49 staff", "50:50 to 249 staff", "250:250 or more staff")),
        F("Input", "website", "Website"),
        F("Dropdown", "registration_country", "Country of registration", required=True, options=COUNTRIES)),
      C("Accordion", "acc_contact", "Buyer contact",
        F("Input", "contact_first_name", "First name", required=True),
        F("Input", "contact_last_name", "Last name", required=True),
        F("Input", "contact_job_title", "Job title"),
        F("Input", "contact_email", "Email", required=True),
        F("Input", "contact_phone", "Phone", required=True)),
      C("Accordion", "acc_ap", "Accounts payable",
        F("Input", "ap_name", "Accounts payable contact"),
        F("Input", "ap_email", "Accounts payable email"),
        F("Input", "ap_phone", "Accounts payable phone"))),
    C("Tab", "tab_addresses", "2. Addresses",
      C("Accordion", "acc_billing", "Billing address",
        *_address("billing", "Billing"),
        F("Input", "invoice_email", "Email for invoices", required=True)),
      C("Accordion", "acc_delivery", "Delivery address",
        F("Checkbox", "same_as_billing", "Deliver to the billing address"),
        *_address("delivery", "Delivery"),
        F("Input", "delivery_phone", "Delivery: phone on site", required=True),
        F("Checkbox", "loading_dock", "There is a loading dock"),
        F("TextArea", "delivery_instructions", "Delivery instructions"),
        F("DatePicker", "delivery_date", "Requested delivery date", required=True),
        F("Checkbox", "partial_delivery", "Partial deliveries are fine"),
        F("Dropdown", "incoterms", "Delivery terms",
          options=opts("dap:Delivered at place (DAP)", "ddp:Delivered duty paid (DDP)", "exw:Collect from our warehouse (EXW)")))),
    C("Tab", "tab_items", "3. Line items",
      C("Accordion", "acc_items", "Order lines",
        "SKUs look like ABC-12345 (3 letters, a dash, 4 to 6 digits). Prices exclude VAT. Minimum order 500 EUR.",
        F("NumberInput", "item_count", "Number of order lines (1 to 10)", required=True),
        *[f for i in range(1, MAX_ITEMS + 1) for f in _item(i)])),
    C("Tab", "tab_payment", "4. Totals and payment",
      C("Accordion", "acc_totals", "Totals",
        F("Input", "subtotal", "Subtotal (EUR, excl. VAT, calculated)", readonly=True),
        F("Input", "vat_amount", "VAT 21% (EUR, calculated)", readonly=True),
        F("Input", "total", "Total (EUR, incl. VAT, calculated)", readonly=True)),
      C("Accordion", "acc_payment", "Payment",
        "Net 30 days is available for orders above 5000 EUR before VAT.",
        F("Dropdown", "payment_terms", "Payment terms", required=True, options=TERMS),
        F("Input", "po_reference", "Your PO reference", required=True),
        F("Input", "cost_centre", "Cost centre"),
        F("Input", "refund_account_holder", "Refund account holder", required=True),
        F("Input", "refund_iban", "IBAN for refunds", required=True, placeholder="NL91ABNA0417164300"),
        F("Input", "refund_bic", "BIC"))),
    C("Tab", "tab_approval", "5. Approval",
      C("Accordion", "acc_approval", "Approver",
        "The order must be approved by someone other than the buyer contact.",
        F("Input", "approver_name", "Approver's full name", required=True),
        F("Input", "approver_role", "Approver's job title", required=True),
        F("Input", "approver_email", "Approver's email", required=True),
        F("Input", "approver_phone", "Approver's phone"),
        F("TextArea", "order_notes", "Notes for the supplier"),
        F("Checkbox", "accept_terms", "I accept Northgate Supply's terms of sale", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Purchase order: Northgate Supply",
    "starters": ["Place a business order", "Can we pay in 30 days?", "What is the minimum order?"],
    "persona": "You are Northgate Supply's order desk assistant. Be precise with numbers; never invent prices or SKUs.",
    "flow_hints": [
        "The tabs unlock one by one: buyer, addresses, line items, totals and payment, approval.",
        "The EU VAT id is two letters and 8 to 12 digits, e.g. NL123456789012.",
        "Totals are calculated: subtotal, VAT 21% and total; the minimum order is 500 EUR before VAT.",
        "Net 30 days is offered only above 5000 EUR before VAT.",
        "The approver must be a different person from the buyer contact.",
    ],
    "glossary": {
        "vat_id": "EU VAT id: two letters (the country of registration) and 8 to 12 digits, no spaces.",
        "item_count": "1 to 10 order lines.",
        "subtotal": "The sum of the line totals before VAT; at least 500 EUR.",
        "payment_terms": "Prepayment or company card always; Net 30 only for a subtotal above 5000 EUR.",
        "refund_iban": "The account refunds are paid to.",
        "approver_email": "Must differ from the buyer contact's email.",
    },
    "pii": ["contact_email", "contact_phone", "invoice_email", "delivery_phone", "refund_iban", "approver_email"],
}

PAGE = {
    "path": "/lab/purchase-order",
    "title": "Northgate Supply: purchase order",
    "description": "Northgate Supply's B2B purchase order form for registered businesses in the EU.",
    "keywords": ["purchase order", "b2b", "wholesale", "order", "supplier", "invoice", "vat"],
    "sections": [
        {"id": "terms", "title": "Ordering terms",
         "text": "Minimum order 500 EUR before VAT. Prices exclude VAT; VAT is 21%. Up to 10 lines per order. "
                 "Payment by prepayment or company card; Net 30 days only for orders above 5000 EUR before VAT. "
                 "Delivery at least 3 working days after the order. The EU VAT id is two letters (the country of "
                 "registration) and 8 to 12 digits."},
        {"id": "approval", "title": "Approval",
         "text": "Every order needs an approver who is not the buyer contact."},
    ],
}


def _workdays_ahead(n: int) -> date:
    d = date.today()
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def rules(h) -> None:
    h.match("vat_id", r"[A-Za-z]{2}\d{8,12}", "A VAT id is two letters and 8 to 12 digits, like NL123456789012")
    h.match("website", r"(https?://)?[\w.-]+\.[a-z]{2,}(/\S*)?", "Enter a web address, like example.com")
    h.email("contact_email")
    h.phone("contact_phone")
    h.email("invoice_email")
    h.email("ap_email")
    h.phone("ap_phone")
    vat, reg = h.text("vat_id").upper(), h.id("registration_country")
    if reg and len(vat) >= 2 and vat[:2].isalpha() and vat[:2] != reg:
        h.error("vat_id", f"The VAT id must start with the country of registration ({reg})")

    same = h.on("same_as_billing")
    h.show(*DELIVERY, when=not same)
    h.require(*[n for n in DELIVERY if n != "delivery_street2"], when=not same)
    h.phone("delivery_phone")
    h.a_date("delivery_date", after=_workdays_ahead(3), msg="Delivery is at least 3 working days from today")

    h.number("item_count", 1, MAX_ITEMS, msg="An order has 1 to 10 lines", integer=True)
    k = h.repeat("item_count", ITEM_GROUPS, required=("_sku", "_description", "_quantity", "_unit", "_unit_price"))
    subtotal, complete = 0.0, k > 0
    for i in range(1, MAX_ITEMS + 1):
        h.match(f"item_{i}_sku", r"[A-Za-z]{3}-\d{4,6}", "A SKU is 3 letters, a dash and 4 to 6 digits, like ABC-12345")
        h.number(f"item_{i}_quantity", 1, 10000, integer=True)
        h.number(f"item_{i}_unit_price", 0.01, 1_000_000, msg="The unit price must be above 0")
        h.number(f"item_{i}_discount", 0, 30, msg="The discount is 0 to 30%")
        if i > k:
            continue
        q, p = h.num(f"item_{i}_quantity"), h.num(f"item_{i}_unit_price")
        disc = h.num(f"item_{i}_discount") or 0
        bad = any(h.has_error(f"item_{i}_{x}") for x in ("quantity", "unit_price", "discount"))
        if q is None or p is None or bad:
            complete = False
            continue
        line = round(q * p * (1 - disc / 100), 2)
        h.set(f"item_{i}_line_total", line)
        subtotal += line
    if complete:
        subtotal = round(subtotal, 2)
        vat = round(subtotal * VAT, 2)
        h.set("subtotal", subtotal)
        h.set("vat_amount", vat)
        h.set("total", round(subtotal + vat, 2))
        if subtotal < MIN_ORDER and not h.has_error("item_count"):
            h.error("item_count", f"The minimum order is 500 EUR before VAT (now {subtotal:.2f} EUR): add lines or quantity")
    net30 = complete and subtotal > NET30_FROM
    h.options("payment_terms", TERMS if net30 else [o for o in TERMS if o["id"] != "net30"])
    if h.id("payment_terms") == "net30" and not net30:
        h.clear("payment_terms")

    h.iban("refund_iban")
    h.match("refund_bic", r"[A-Za-z]{4}[A-Za-z]{2}[A-Za-z0-9]{2}([A-Za-z0-9]{3})?", "A BIC has 8 or 11 letters and digits")
    h.email("approver_email")
    h.phone("approver_phone")
    a, c = h.text("approver_email").lower(), h.text("contact_email").lower()
    if a and a == c:
        h.error("approver_email", "The approver must be someone other than the buyer contact")
