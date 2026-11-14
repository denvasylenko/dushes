"""Lab form: a service request on an old municipal utility portal (DELIBERATELY BAD, to test the assistant on
a form that explains nothing).

The oddities, on purpose:
- cryptic labels: "Fld_07" (the meter number, 8 digits), "Ref. no. (see p.2)" (the bill reference, R + 6 digits,
  printed on page 2 of the paper bill), "Svc." (the service code), "Rdg" (a meter reading), "Rem." (remarks);
- "Name" is used twice: `appl_nm` is the applicant's name, `co_nm` the company's name;
- three fields have no label at all: `txt1` (house number), `txt2` (postcode, 4 digits), `chk_a` (accepting the
  terms; the static text above it says "Tick below (Reg. 14/b)");
- `sess_tok` is hidden (visible=False) and no rule ever shows it;
- `cust_id` is read-only and prefilled by the rules (h.set) with the portal's customer id;
- the "Svc." dropdown's options are bare codes (A1, B7, C3, D9, X0): their meaning is only on the page;
- the date field is labelled "DD/MM/YY", but the backend stores and validates an ISO date (YYYY-MM-DD);
- two elements share one `name`: the "Tel." input appears in the applicant section and again in the company
  section, both `name="tel"` (FORM_JSX is patched by hand; props and state have one `tel` entry, so both show and
  write the same value).

Rules: appl_nm, tel, svc_code and chk_a are required; ref_no is R + 6 digits; Fld_07 is 8 digits; txt2 is 4 digits.
A1 (new connection) and D9 (disconnection) need the date, today or later; B7 (meter reading dispute) needs Fld_07 and
Rdg; C3 (change of account holder) needs the company name; X0 (other) needs remarks.
"""
from __future__ import annotations

from ..dsl import C, F, opts, to_jsx

FORM_ID = "weird_legacy_portal"
CUSTOMER_ID = "0048213-NB"

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_1", "Pg 1",
      C("Accordion", "acc_a", "Sect. A",
        F("Input", "cust_id", "Cust. ID", readonly=True),
        F("Input", "ref_no", "Ref. no. (see p.2)"),
        F("Input", "fld_07", "Fld_07"),
        F("Input", "appl_nm", "Name", required=True),
        F("Input", "txt1", ""),
        F("Input", "txt2", ""),
        F("Input", "tel", "Tel.", required=True),
        F("Input", "sess_tok", "Session", visible=False)),
      C("Accordion", "acc_b", "Sect. B (if appl.)",
        F("Input", "co_nm", "Name"))),
    C("Tab", "tab_2", "Pg 2",
      C("Accordion", "acc_c", "Sect. C",
        F("Dropdown", "svc_code", "Svc.", required=True,
          options=opts("A1:A1", "B7:B7", "C3:C3", "D9:D9", "X0:X0")),
        F("DatePicker", "eff_dt", "DD/MM/YY"),
        F("Input", "rdg", "Rdg"),
        F("TextArea", "rem", "Rem."),
        "Tick below (Reg. 14/b).",
        F("Checkbox", "chk_a", "", required=True))),
)

# the "Tel." input appears a second time, in Sect. B, with the same name
_jsx = to_jsx(FORM)
_co = '<Input name="co_nm" />'
assert _co in _jsx
_pad = _jsx.split(_co)[0].rsplit("\n", 1)[1]
FORM_JSX = _jsx.replace(_co, f'{_co}\n{_pad}<Input name="tel" />')

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Utility service request",
    "starters": ["I'm moving in and need water connected", "I dispute my meter reading", "What is Fld_07?"],
    "persona": "You are Northbrook Municipal Utilities' portal assistant. The form is old and cryptic: translate its "
               "labels into plain words for the user.",
    "flow_hints": [
        "Pg 1 is about the applicant, Pg 2 about the request.",
        "Svc. codes: A1 new connection, B7 meter reading dispute, C3 change of account holder, D9 disconnection, X0 other.",
        "The first 'Name' is the applicant, the second (Sect. B) the company, only when applying for a company.",
    ],
    "glossary": {
        "fld_07": "The water meter number: 8 digits on the meter's face plate.",
        "ref_no": "The bill reference on page 2 of the paper bill: R followed by 6 digits.",
        "txt1": "House number.",
        "txt2": "Postcode: 4 digits.",
        "chk_a": "Accepting the terms of supply (Regulation 14/b).",
        "eff_dt": "The date the connection or disconnection should take effect (today or later).",
        "rdg": "The meter reading you see, in cubic metres.",
        "rem": "Remarks: required for X0 (other).",
    },
    "pii": ["appl_nm", "tel", "ref_no"],
}

PAGE = {
    "path": "/lab/utility-portal",
    "title": "Northbrook Municipal Utilities: service request",
    "description": "Northbrook Municipal Utilities, water and waste: the online service request form (legacy portal).",
    "keywords": ["water", "utility", "meter", "municipal", "connection", "disconnection", "bill"],
    "sections": [
        {"id": "codes", "title": "Service codes (Svc.)",
         "text": "A1 = new connection. B7 = meter reading dispute. C3 = change of account holder. "
                 "D9 = disconnection. X0 = other request (describe it in Rem.)."},
        {"id": "help", "title": "Filling in the form",
         "text": "Fld_07 is your 8-digit meter number. The reference number (R and 6 digits) is on page 2 of your "
                 "paper bill. After the street name come your house number and your 4-digit postcode. "
                 "Connections and disconnections take effect on the date you choose, today at the earliest."},
    ],
}


def rules(h) -> None:
    h.set("cust_id", CUSTOMER_ID)
    h.match("ref_no", r"[Rr]\d{6}", "Use R followed by 6 digits (page 2 of your bill)")
    h.match("fld_07", r"\d{8}", "The meter number has 8 digits")
    h.match("txt2", r"\d{4}", "The postcode has 4 digits")
    h.phone("tel")
    code = h.id("svc_code")
    h.require("eff_dt", when=code in ("A1", "D9"))
    h.a_date("eff_dt", future=True, msg="The date must be today or later")
    h.require("fld_07", "rdg", when=code == "B7")
    h.number("rdg", 0, 999999, msg="Enter the reading in cubic metres (0 to 999999)")
    h.require("co_nm", when=code == "C3")
    h.require("rem", when=code == "X0")
