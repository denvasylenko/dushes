"""Lab form: a simple personal income tax return for the tax year 2025 at the Norland Tax Office (medium-big, repeating groups).

The Norland tax id (TIN) has 9 digits; the 9th is a check digit: multiply digits 1 to 8 by the weights 1, 2, ..., 8,
add them up and take the remainder of the sum divided by 11; that remainder is the 9th digit (ids whose remainder is
10 are never issued). Example: 12345678 -> 1*1 + 2*2 + ... + 8*8 = 204, 204 mod 11 = 6, so 123456786 is valid.

Rules: the TIN (and the spouse's TIN when married) passes the check; employers are a repeating group of 1 to 4
(name, gross pay, tax withheld; withheld cannot exceed gross); dependents are a repeating group of 0 to 6 (name and
birth date; a dependent is under 18 on 31 December 2025); each picked deduction reveals its amount (required), the
pension deduction is capped at 40,000 NKR; the read-only totals follow the flat rule stated on the page:
taxable income = gross pay + other income - deductions - 50,000 personal allowance - 20,000 per dependent (never below
0); tax = 22% of taxable income; estimated refund = tax withheld - tax (a negative value is tax to pay). The refund IBAN
and account holder are required when the refund is positive.
"""
from __future__ import annotations

from datetime import date

from ..dsl import C, F, opts

FORM_ID = "tax_return_simple"
SEQUENTIAL = False

TAX_YEAR = 2025
ALLOWANCE, PER_DEPENDENT, RATE, PENSION_CAP = 50000, 20000, 0.22, 40000
MAX_EMP, MAX_DEP = 4, 6
DEDUCTIONS = opts("pension:Private pension contributions", "mortgage:Mortgage interest", "charity:Gifts to charity",
                  "commuting:Commuting costs", "union:Trade union fees")

EMP_GROUPS = [[f"employer_{i}_{s}" for s in ("name", "gross", "withheld")] for i in range(1, MAX_EMP + 1)]
DEP_GROUPS = [[f"dependent_{i}_{s}" for s in ("name", "birth_date")] for i in range(1, MAX_DEP + 1)]


def _emp(i: int) -> list:
    p = f"employer_{i}_"
    return [f"Employer {i}",
            F("Input", p + "name", f"Employer {i}: name", required=True),
            F("NumberInput", p + "gross", f"Employer {i}: gross pay in {TAX_YEAR}, NKR", required=True),
            F("NumberInput", p + "withheld", f"Employer {i}: tax withheld, NKR", required=True)]


def _dep(i: int) -> list:
    p = f"dependent_{i}_"
    return [F("Input", p + "name", f"Child {i}: full name", required=True),
            F("DatePicker", p + "birth_date", f"Child {i}: date of birth", required=True)]


FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_you", "1. You",
      C("Accordion", "acc_you", "Taxpayer",
        F("Input", "tax_id", "Tax id (TIN, 9 digits)", required=True, placeholder="123456786"),
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "address", "Street and number", required=True),
        F("Input", "postcode", "Postcode (4 digits)", required=True),
        F("Input", "city", "City", required=True),
        F("Input", "phone", "Phone", placeholder="+47 912 34 567"),
        F("Input", "email", "Email", required=True)),
      C("Accordion", "acc_family", "Family",
        F("Dropdown", "marital_status", "Marital status on 31 December 2025", required=True,
          options=opts("single:Single", "married:Married or registered partner", "divorced:Divorced", "widowed:Widowed")),
        F("Input", "spouse_name", "Spouse's full name", required=True),
        F("Input", "spouse_tax_id", "Spouse's tax id", required=True))),
    C("Tab", "tab_income", "2. Income",
      C("Accordion", "acc_employers", "Employment income in 2025",
        F("NumberInput", "employer_count", "How many employers did you have? (1 to 4)", required=True),
        *[x for i in range(1, MAX_EMP + 1) for x in _emp(i)]),
      C("Accordion", "acc_other_income", "Other income",
        F("NumberInput", "other_income", "Other taxable income (interest, rent), NKR"))),
    C("Tab", "tab_dependents", "3. Dependents",
      C("Accordion", "acc_dependents", "Children you support",
        "A dependent child is under 18 on 31 December 2025. Each one lowers taxable income by 20,000 NKR.",
        F("NumberInput", "dependent_count", "Number of dependent children (0 to 6)"),
        *[x for i in range(1, MAX_DEP + 1) for x in _dep(i)])),
    C("Tab", "tab_deductions", "4. Deductions",
      C("Accordion", "acc_deductions", "Deductions",
        F("MultiSelect", "deductions", "Deductions you claim", options=DEDUCTIONS),
        *[F("NumberInput", f"deduction_{o['id']}_amount", f"{o['name']}, NKR", required=True) for o in DEDUCTIONS])),
    C("Tab", "tab_result", "5. Result and refund",
      C("Accordion", "acc_result", "Your estimate",
        "Flat rule: taxable income = gross pay + other income - deductions - 50,000 NKR personal allowance - "
        "20,000 NKR per dependent child (never below 0). Tax = 22% of taxable income. Refund = tax withheld - tax.",
        F("Input", "total_income", "Total income, NKR (calculated)", readonly=True),
        F("Input", "taxable_income", "Taxable income, NKR (calculated)", readonly=True),
        F("Input", "tax_due", "Tax, NKR (calculated)", readonly=True),
        F("Input", "estimated_refund", "Estimated refund, NKR (negative: to pay; calculated)", readonly=True)),
      C("Accordion", "acc_refund", "Refund account",
        F("Input", "refund_iban", "IBAN for the refund", required=True, placeholder="NO93 8601 1117 947"),
        F("Input", "account_holder", "Account holder", required=True),
        F("Checkbox", "declaration", "I confirm that this return is correct and complete", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Personal tax return 2025",
    "starters": ["File my 2025 tax return", "I had two jobs last year", "How big will my refund be?"],
    "persona": "You are the Norland Tax Office's filing assistant. Be exact with numbers; explain the flat rule when asked; "
               "never give personal tax planning advice.",
    "flow_hints": [
        "Ask the number of employers first, then each employer's gross pay and tax withheld.",
        "Ask the number of dependent children, then each child's name and date of birth.",
        "The totals on the last tab are calculated: never ask the user to type them.",
        "The refund account is needed only when the estimate is a refund.",
    ],
    "glossary": {
        "tax_id": "9 digits; the 9th is a check digit: digits 1-8 times weights 1-8, summed, remainder of division by 11. "
                  "Example of a valid id: 123456786.",
        "taxable_income": "Gross pay + other income - deductions - 50,000 NKR personal allowance - 20,000 NKR per "
                          "dependent child, never below 0.",
        "tax_due": "22% of taxable income (a flat rate).",
        "estimated_refund": "Tax withheld minus tax; a negative number is tax still to pay.",
        "deduction_pension_amount": "Private pension contributions are deductible up to 40,000 NKR.",
        "dependent_count": "Children under 18 on 31 December 2025, at most 6.",
        "postcode": "Norland postcodes have 4 digits.",
    },
    "pii": ["tax_id", "first_name", "last_name", "birth_date", "address", "phone", "email", "spouse_tax_id",
            "refund_iban", "account_holder"],
}

PAGE = {
    "path": "/lab/norland-tax",
    "title": "Norland Tax Office: personal tax return 2025",
    "description": "File a simple personal income tax return for 2025 with the Norland Tax Office.",
    "keywords": ["tax", "tax return", "income tax", "refund", "norland", "deductions"],
    "sections": [
        {"id": "rule", "title": "How the estimate is calculated",
         "text": "Taxable income = gross pay + other income - deductions - 50,000 NKR personal allowance - 20,000 NKR "
                 "for each dependent child under 18 on 31 December 2025, never below 0. Tax is a flat 22% of taxable "
                 "income. Your refund is the tax withheld by your employers minus that tax. Private pension "
                 "contributions are deductible up to 40,000 NKR."},
        {"id": "deadline", "title": "Deadline",
         "text": "File by 30 April 2026. Refunds are paid to the IBAN you give within 6 weeks."},
    ],
}


def tin_ok(v: str) -> bool:
    """The Norland TIN check: 9 digits, digit 9 = sum(digit_i * i for i in 1..8) mod 11."""
    if len(v) != 9 or not v.isdigit():
        return False
    r = sum(int(c) * w for c, w in zip(v[:8], range(1, 9))) % 11
    return r != 10 and r == int(v[8])


def _tin(h, n: str) -> None:
    v = h.text(n).replace(" ", "")
    if v and not tin_ok(v):
        h.error(n, "A tax id has 9 digits and a valid check digit; check it against your tax card")


def rules(h) -> None:
    _tin(h, "tax_id")
    h.a_date("birth_date", past=True)
    h.match("postcode", r"\d{4}", "A Norland postcode has 4 digits")
    h.phone("phone")
    h.email("email")
    married = h.id("marital_status") == "married"
    h.show("spouse_name", "spouse_tax_id", when=married)
    h.require("spouse_name", "spouse_tax_id", when=married)
    _tin(h, "spouse_tax_id")
    if married and h.text("spouse_tax_id") and h.text("spouse_tax_id") == h.text("tax_id"):
        h.error("spouse_tax_id", "This is your own tax id; enter your spouse's")

    # employers
    h.number("employer_count", lo=1, hi=MAX_EMP, integer=True, msg="Enter 1 to 4 employers")
    k = h.repeat("employer_count", EMP_GROUPS, required=("_name", "_gross", "_withheld"))
    gross = withheld = 0.0
    for i in range(1, k + 1):
        p = f"employer_{i}_"
        h.number(p + "gross", lo=0, msg="Gross pay cannot be negative")
        h.number(p + "withheld", lo=0, msg="Tax withheld cannot be negative")
        g, w = h.num(p + "gross"), h.num(p + "withheld")
        if g is not None and w is not None and w > g:
            h.error(p + "withheld", "Tax withheld cannot be more than the gross pay")
        gross += max(g or 0, 0)
        withheld += max(w or 0, 0)
    h.number("other_income", lo=0, msg="Other income cannot be negative")
    other = max(h.num("other_income") or 0, 0)

    # dependents
    h.number("dependent_count", lo=0, hi=MAX_DEP, integer=True, msg="Enter 0 to 6 children")
    d = h.repeat("dependent_count", DEP_GROUPS, required=("_name", "_birth_date"))
    end = date(TAX_YEAR, 12, 31)
    for i in range(1, d + 1):
        n = f"dependent_{i}_birth_date"
        h.a_date(n, before=end, msg="The child must be born by 31 December 2025")
        a = h.age(n, on=end)
        if a is not None and a >= 18 and not h.has_error(n):
            h.error(n, "A dependent child is under 18 on 31 December 2025")

    # deductions
    picked = set(h.ids("deductions"))
    total_ded = 0.0
    for o in DEDUCTIONS:
        n = f"deduction_{o['id']}_amount"
        on = o["id"] in picked
        h.show(n, when=on)
        h.require(n, when=on)
        if on:
            h.number(n, lo=0, msg="An amount cannot be negative")
            total_ded += max(h.num(n) or 0, 0)
    if "pension" in picked:
        h.number("deduction_pension_amount", lo=0, hi=PENSION_CAP, msg="Pension contributions are deductible up to 40,000 NKR")
        total_ded -= max((h.num("deduction_pension_amount") or 0) - PENSION_CAP, 0)

    # the estimate (only once the income is known)
    if k:
        income = gross + other
        taxable = max(income - total_ded - ALLOWANCE - PER_DEPENDENT * d, 0)
        tax = round(taxable * RATE)
        refund = round(withheld - tax)
        h.set("total_income", str(round(income)))
        h.set("taxable_income", str(round(taxable)))
        h.set("tax_due", str(tax))
        h.set("estimated_refund", str(refund))
    else:
        refund = 0
    pay = refund > 0
    h.show("refund_iban", "account_holder", when=pay)
    h.require("refund_iban", "account_holder", when=pay)
    h.iban("refund_iban")
