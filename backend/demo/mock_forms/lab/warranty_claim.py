"""Lab form: a warranty repair claim for electronics in the UK (medium; dependent options, regex by category, uploads).

Rules: the models depend on the category; the serial number format depends on the category; the purchase date is in
the past and within the last 2 years (else "out of warranty"); the fault description has at least 20 characters;
the receipt is required; a refund is offered only within 30 days of purchase (it is removed from the options after
that, and an error if still chosen); the return address uses a UK postcode.
"""
from __future__ import annotations

import re
from datetime import date

from ..dsl import C, F, opts

FORM_ID = "warranty_claim"

MODELS = {
    "phone": opts("nova_s3:Nova S3", "nova_s3_max:Nova S3 Max", "nova_lite:Nova Lite"),
    "laptop": opts("aero_13:Aerobook 13", "aero_15:Aerobook 15 Pro", "aero_flip:Aerobook Flip"),
    "headphones": opts("hush_one:Hush One", "hush_buds:Hush Buds", "hush_pro:Hush Pro"),
    "tv": opts("vista_43:Vista 43\"", "vista_55:Vista 55\" OLED", "vista_65:Vista 65\" OLED"),
}
SERIALS = {   # category: (regex, example)
    "phone": (r"NV\d{8}", "NV12345678"),
    "laptop": (r"AB-\d{4}-[A-Z0-9]{6}", "AB-2025-7KX93Q"),
    "headphones": (r"\d{12}", "123456789012"),
    "tv": (r"TV[A-Z]\d{9}", "TVK123456789"),
}
RESOLUTION = opts("repair:Repair", "replace:Replacement", "refund:Refund (within 30 days of purchase)")

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_product", "1. Product",
      C("Accordion", "acc_product", "The product",
        F("Dropdown", "category", "Product category", required=True,
          options=opts("phone:Phone", "laptop:Laptop", "headphones:Headphones", "tv:TV")),
        F("Dropdown", "model", "Model", required=True, options=[]),
        F("Input", "serial_number", "Serial number", required=True),
        F("DatePicker", "purchase_date", "Purchase date", required=True),
        F("Input", "retailer", "Where did you buy it?"),
        F("FileUpload", "receipt", "Receipt or invoice", required=True))),
    C("Tab", "tab_fault", "2. Fault",
      C("Accordion", "acc_fault", "What is wrong",
        F("TextArea", "fault_description", "Describe the fault (at least 20 characters)", required=True),
        F("DatePicker", "fault_start", "When did it start?"),
        F("Checkbox", "physical_damage", "The product was dropped or got wet"),
        F("FileUpload", "photos", "Photos of the fault", multiple=True),
        F("RadioGroup", "resolution", "Preferred resolution", required=True, options=RESOLUTION))),
    C("Tab", "tab_return", "3. Contact and return",
      C("Accordion", "acc_contact", "Contact",
        F("Input", "full_name", "Full name", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Phone")),
      C("Accordion", "acc_address", "Return shipping address",
        "We send the repaired or replacement product to this address, free of charge.",
        F("Input", "address_line1", "Address line 1", required=True),
        F("Input", "address_line2", "Address line 2"),
        F("Input", "town", "Town or city", required=True),
        F("Input", "postcode", "Postcode", required=True, placeholder="M1 1AE"))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Warranty claim",
    "starters": ["My laptop screen flickers", "Can I get a refund for headphones I bought last week?",
                 "Where do I find the serial number?"],
    "persona": "You are Brightwell Electronics' warranty assistant. Be calm and practical.",
    "flow_hints": [
        "Category first: the models and the serial number format depend on it.",
        "The warranty lasts 2 years from purchase; older products are out of warranty.",
        "A refund is possible only within 30 days of purchase; after that, repair or replacement.",
        "The receipt upload is required.",
    ],
    "glossary": {
        "serial_number": "Phone NV + 8 digits (NV12345678); laptop AB-year-6 characters (AB-2025-7KX93Q); headphones 12 digits; "
                         "TV TV + a letter + 9 digits (TVK123456789). It is on the box and in the settings.",
        "purchase_date": "The warranty covers 2 years from the purchase date.",
        "resolution": "Repair or replacement within the warranty; refund only within 30 days of purchase.",
        "physical_damage": "Drops and liquid damage are not covered by the warranty; we will quote a paid repair.",
    },
    "pii": ["full_name", "email", "phone", "address_line1", "address_line2", "postcode"],
}

PAGE = {
    "path": "/lab/warranty",
    "title": "Brightwell Electronics: warranty claim",
    "description": "Brightwell Electronics' warranty repair claim form for phones, laptops, headphones and TVs.",
    "keywords": ["warranty", "repair", "broken", "refund", "replacement", "electronics", "claim"],
    "sections": [
        {"id": "warranty", "title": "Our warranty",
         "text": "2 years from the purchase date, with the receipt. Refunds only within 30 days of purchase; after that we "
                 "repair or replace. Drops and liquid damage are not covered. Return shipping is free."},
        {"id": "serial", "title": "Serial number formats",
         "text": "Phone: NV and 8 digits (NV12345678). Laptop: AB-year-6 characters (AB-2025-7KX93Q). Headphones: 12 "
                 "digits. TV: TV, a letter and 9 digits (TVK123456789)."},
    ],
}


def _years_ago(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:   # 29 February
        return d.replace(year=d.year - years, day=28)


def rules(h) -> None:
    cat = h.id("category")
    h.show("model", when=cat in MODELS)
    h.options("model", MODELS.get(cat or "", []))
    if cat in SERIALS:
        rx, ex = SERIALS[cat]
        sn = h.text("serial_number").upper()
        if sn and not re.fullmatch(rx, sn):
            h.error("serial_number", f"This serial number does not fit a {cat}: it looks like {ex}")

    today = date.today()
    pd = h.date("purchase_date")
    h.a_date("purchase_date", past=True)
    if pd and not h.has_error("purchase_date") and pd < _years_ago(today, 2):
        h.error("purchase_date", "Out of warranty: the warranty covers 2 years from purchase")
    recent = pd is not None and not h.has_error("purchase_date") and (today - pd).days <= 30
    if pd is not None and not recent:
        h.options("resolution", [o for o in RESOLUTION if o["id"] != "refund"])
        if h.id("resolution") == "refund":
            h.error("resolution", "A refund is possible only within 30 days of purchase: choose repair or replacement")

    h.length("fault_description", 20, msg="Describe the fault in at least 20 characters")
    h.a_date("fault_start", past=True)
    h.email("email")
    h.phone("phone")
    h.match("postcode", r"[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}", "Enter a UK postcode, like M1 1AE")
