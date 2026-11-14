"""Lab form: a UK mortgage agreement in principle (huge: 115 fields, 6 sequential tabs, loops for repeated groups).

Rules: the co-applicant tab and income section appear only when applying with someone; each applicant is 18 to 75;
fewer than 3 years at the address reveals the previous address; employed reveals the job and salary, self-employed
reveals the business and two years of profit (trading for 2 years or more), retired reveals the pension; up to 6
monthly debts (a count shows them); a gifted deposit reveals the gifter; the loan, the LTV %, the estimated monthly
payment (5.0% a year) and the debt-to-income % are computed; a deposit below 10% of the price is an error and a
debt-to-income ratio above 45% is an error on the summary.
"""
from __future__ import annotations

import re

from ..dsl import C, F, opts

FORM_ID = "mortgage_preapproval"
SEQUENTIAL = True
RATE = 0.05          # the illustrative annual rate for the estimate
DTI_LIMIT = 45.0     # %
MIN_DEPOSIT = 0.10   # of the price
MAX_DEBTS = 6
PEOPLE = ("app_", "co_")

PERSON = ["title", "first_name", "last_name", "birth_date", "ni_number", "email", "phone", "marital_status",
          "dependants", "address_line", "city", "postcode", "years_at_address", "residency",
          "prev_address_line", "prev_postcode"]
INCOME = ["employment_status", "employer", "job_title", "employment_start", "annual_salary", "annual_bonus",
          "business_name", "trading_start", "profit_year1", "profit_year2", "annual_pension", "other_income",
          "other_income_source"]
DEBT = ["type", "lender", "monthly", "balance", "cleared"]
DEBTS = [[f"debt_{i}_{s}" for s in DEBT] for i in range(1, MAX_DEBTS + 1)]


def person(p: str) -> list:
    return [
        F("Dropdown", f"{p}title", "Title", options=opts("mr:Mr", "mrs:Mrs", "ms:Ms", "mx:Mx", "dr:Dr")),
        F("Input", f"{p}first_name", "First name", required=True),
        F("Input", f"{p}last_name", "Last name", required=True),
        F("DatePicker", f"{p}birth_date", "Date of birth", required=True),
        F("Input", f"{p}ni_number", "National Insurance number", required=True, placeholder="AB 12 34 56 C"),
        F("Input", f"{p}email", "Email", required=True),
        F("Input", f"{p}phone", "Mobile phone", required=True, placeholder="+44 7700 900123"),
        F("Dropdown", f"{p}marital_status", "Marital status", required=True,
          options=opts("single:Single", "married:Married or civil partnership", "cohabiting:Living together",
                       "divorced:Divorced or separated", "widowed:Widowed")),
        F("NumberInput", f"{p}dependants", "Number of financial dependants"),
        F("Input", f"{p}address_line", "Current address", required=True),
        F("Input", f"{p}city", "Town or city", required=True),
        F("Input", f"{p}postcode", "Postcode", required=True, placeholder="SW1A 1AA"),
        F("NumberInput", f"{p}years_at_address", "Years at this address", required=True),
        F("Dropdown", f"{p}residency", "Residency status", required=True,
          options=opts("citizen:UK or Irish citizen", "settled:Settled or pre-settled status", "visa:On a visa")),
        F("Input", f"{p}prev_address_line", "Previous address", required=True),
        F("Input", f"{p}prev_postcode", "Previous postcode", required=True),
    ]


def income(p: str) -> list:
    return [
        F("Dropdown", f"{p}employment_status", "Employment status", required=True,
          options=opts("employed:Employed", "self_employed:Self-employed", "retired:Retired", "not_working:Not working")),
        F("Input", f"{p}employer", "Employer", required=True),
        F("Input", f"{p}job_title", "Job title", required=True),
        F("DatePicker", f"{p}employment_start", "Started this job on", required=True),
        F("NumberInput", f"{p}annual_salary", "Basic salary, GBP a year (before tax)", required=True),
        F("NumberInput", f"{p}annual_bonus", "Regular bonus and overtime, GBP a year"),
        F("Input", f"{p}business_name", "Business name", required=True),
        F("DatePicker", f"{p}trading_start", "Trading since", required=True),
        F("NumberInput", f"{p}profit_year1", "Net profit, last full year, GBP", required=True),
        F("NumberInput", f"{p}profit_year2", "Net profit, the year before, GBP", required=True),
        F("NumberInput", f"{p}annual_pension", "Pension income, GBP a year", required=True),
        F("NumberInput", f"{p}other_income", "Other income, GBP a year"),
        F("Input", f"{p}other_income_source", "Source of the other income", required=True),
    ]


def debt(i: int) -> list:
    return [
        F("Dropdown", f"debt_{i}_type", f"Debt {i}: type", options=opts(
            "card:Credit card", "loan:Personal loan", "car:Car finance", "student:Student loan", "other:Other")),
        F("Input", f"debt_{i}_lender", f"Debt {i}: lender"),
        F("NumberInput", f"debt_{i}_monthly", f"Debt {i}: monthly payment, GBP"),
        F("NumberInput", f"debt_{i}_balance", f"Debt {i}: balance left, GBP"),
        F("Checkbox", f"debt_{i}_cleared", f"Debt {i}: will be paid off before the mortgage starts"),
    ]


FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_applicant", "1. Applicant",
      C("Accordion", "acc_applicant", "About you",
        "An agreement in principle shows how much we could lend. It is not a mortgage offer.",
        *person("app_"),
        F("RadioGroup", "applying_with", "Are you applying alone?", required=True,
          options=opts("alone:Just me", "joint:With someone else")))),
    C("Tab", "tab_co", "2. Co-applicant",
      C("Accordion", "acc_co", "The second applicant",
        F("Dropdown", "co_relationship", "Relationship to you", required=True,
          options=opts("spouse:Spouse or civil partner", "partner:Partner", "family:Family member", "friend:Friend")),
        *person("co_"))),
    C("Tab", "tab_income", "3. Income",
      C("Accordion", "acc_income_app", "Your income", *income("app_")),
      C("Accordion", "acc_income_co", "Co-applicant's income", *income("co_"))),
    C("Tab", "tab_debts", "4. Monthly debts",
      C("Accordion", "acc_debts", "Credit commitments",
        "List up to 6 loans, cards or finance agreements you pay every month. Enter 0 if you have none.",
        F("NumberInput", "debt_count", "How many debts do you pay monthly?", required=True),
        *[f for i in range(1, MAX_DEBTS + 1) for f in debt(i)])),
    C("Tab", "tab_assets", "5. Savings and deposit",
      C("Accordion", "acc_assets", "Savings and other property",
        F("NumberInput", "savings", "Savings, GBP", required=True),
        F("NumberInput", "investments", "Investments, GBP"),
        F("Checkbox", "owns_other_property", "I own another property"),
        F("NumberInput", "other_property_value", "Other property's value, GBP", required=True),
        F("NumberInput", "other_mortgage_balance", "Mortgage left on it, GBP", required=True)),
      C("Accordion", "acc_deposit", "Where the deposit comes from",
        F("Dropdown", "deposit_source", "Main source of the deposit", required=True,
          options=opts("savings:Savings", "sale:Sale of a property", "gift:Gift from family", "inheritance:Inheritance")),
        F("Checkbox", "gifted_deposit", "Part of the deposit is a gift"),
        F("Input", "gifter_name", "Name of the person giving it", required=True),
        F("NumberInput", "gift_amount", "Gift amount, GBP", required=True),
        F("FileUpload", "gift_letter", "Signed gift letter"))),
    C("Tab", "tab_property", "6. Property and summary",
      C("Accordion", "acc_property", "The property",
        F("Input", "property_postcode", "Property postcode (if known)"),
        F("Dropdown", "property_type", "Property type", required=True,
          options=opts("detached:Detached house", "semi:Semi-detached house", "terraced:Terraced house", "flat:Flat")),
        F("RadioGroup", "tenure", "Tenure", required=True, options=opts("freehold:Freehold", "leasehold:Leasehold")),
        F("Checkbox", "new_build", "It is a new build"),
        F("NumberInput", "purchase_price", "Purchase price, GBP", required=True),
        F("NumberInput", "deposit", "Deposit, GBP (at least 10% of the price)", required=True),
        F("NumberInput", "term_years", "Mortgage term, years (5 to 40)", required=True),
        F("RadioGroup", "repayment_type", "Repayment type", required=True,
          options=opts("repayment:Capital and interest", "interest_only:Interest only"))),
      C("Accordion", "acc_summary", "Summary",
        "Estimates use an illustrative rate of 5.0% a year. The debt-to-income ratio must be 45% or less.",
        F("Input", "loan_amount", "Loan amount, GBP (calculated)", readonly=True),
        F("Input", "ltv", "Loan to value, % (calculated)", readonly=True),
        F("Input", "monthly_payment", "Estimated monthly payment, GBP (calculated)", readonly=True),
        F("Input", "dti", "Debt-to-income ratio, % (calculated)", readonly=True),
        F("Checkbox", "declaration", "The information I gave is true and complete", required=True),
        F("Checkbox", "credit_check", "I agree to a soft credit check (it does not affect my credit score)", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Mortgage agreement in principle",
    "starters": ["How much could we borrow together?", "I am self-employed, can I apply?",
                 "We have a 10% deposit on a 300,000 GBP flat"],
    "persona": "You are Harbourstone Building Society's mortgage assistant. Be precise; never promise approval and never "
               "give regulated financial advice.",
    "flow_hints": [
        "Six tabs unlock one by one: applicant, co-applicant (joint applications only), income, debts, savings, property.",
        "Ask early whether they apply alone or with someone: joint applications add a whole tab.",
        "Self-employed applicants need 2 full years of trading and give both years' net profit.",
        "Debts: ask for the number first (0 if none), then each one.",
        "The loan, LTV, monthly payment and debt-to-income ratio are calculated by the form.",
    ],
    "glossary": {
        "deposit": "At least 10% of the purchase price.",
        "ltv": "Loan to value: the loan (price minus deposit) as a percentage of the price.",
        "dti": "Monthly debt payments (not those paid off before the mortgage starts) plus the estimated mortgage payment, "
               "divided by the gross monthly income of all applicants. The limit is 45%.",
        "monthly_payment": "Estimated at an illustrative 5.0% a year over the chosen term; interest-only pays interest alone.",
        "employment_status": "Income counted: salary plus bonus (employed), the average of two years' profit (self-employed), "
                             "pension (retired), plus other income.",
        "ni_number": "Two letters, six digits and a letter A to D, for example AB 12 34 56 C.",
    },
    "pii": [f"{p}{n}" for p in PEOPLE for n in ("ni_number", "email", "phone", "address_line", "postcode", "birth_date",
                                                 "prev_address_line", "prev_postcode")],
}

PAGE = {
    "path": "/lab/mortgage",
    "title": "Harbourstone Building Society: mortgage in principle",
    "description": "Harbourstone Building Society's mortgage agreement in principle form for buyers in the UK.",
    "keywords": ["mortgage", "home loan", "house", "buy", "deposit", "borrow", "agreement in principle"],
    "sections": [
        {"id": "limits", "title": "Lending rules",
         "text": "Deposit of at least 10% of the price. The debt-to-income ratio (monthly debts plus the mortgage payment, "
                 "divided by gross monthly income) must be 45% or less. Terms from 5 to 40 years. Applicants aged 18 to 75."},
        {"id": "estimate", "title": "How we estimate",
         "text": "The monthly payment is estimated at an illustrative rate of 5.0% a year. Self-employed income is the "
                 "average of the last two years' net profit, with at least 2 years of trading. "
                 "An agreement in principle is not a mortgage offer."},
    ],
}


def _person_rules(h, p: str, shown: bool) -> None:
    names = [f"{p}{n}" for n in PERSON]
    if not shown:
        h.show(*names, when=False)
        h.require(*names, when=False)
        return
    age = h.age(f"{p}birth_date")
    h.a_date(f"{p}birth_date", past=True)
    if age is not None and not h.has_error(f"{p}birth_date") and not 18 <= age <= 75:
        h.error(f"{p}birth_date", "Applicants must be 18 to 75 years old")
    ni = re.sub(r"\s", "", h.text(f"{p}ni_number")).upper()
    if ni and not re.fullmatch(r"[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]", ni):
        h.error(f"{p}ni_number", "A National Insurance number looks like AB 12 34 56 C")
    h.email(f"{p}email")
    h.phone(f"{p}phone")
    h.number(f"{p}dependants", 0, 10, integer=True)
    pc = r"[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}"
    h.match(f"{p}postcode", pc, "Enter a UK postcode, like SW1A 1AA")
    h.number(f"{p}years_at_address", 0, 99)
    yrs = h.num(f"{p}years_at_address")
    prev = yrs is not None and yrs < 3
    h.show(f"{p}prev_address_line", f"{p}prev_postcode", when=prev)
    h.require(f"{p}prev_address_line", f"{p}prev_postcode", when=prev)
    h.match(f"{p}prev_postcode", pc, "Enter a UK postcode, like SW1A 1AA")


def _income_rules(h, p: str, shown: bool) -> float:
    """Shows the fields for the status and returns the gross yearly income counted."""
    names = [f"{p}{n}" for n in INCOME]
    if not shown:
        h.show(*names, when=False)
        h.require(*names, when=False)
        return 0.0
    st = h.id(f"{p}employment_status")
    emp, se, ret = st == "employed", st == "self_employed", st == "retired"
    groups = {
        "employed": ["employer", "job_title", "employment_start", "annual_salary", "annual_bonus"],
        "self_employed": ["business_name", "trading_start", "profit_year1", "profit_year2"],
        "retired": ["annual_pension"],
    }
    for key, fields in groups.items():
        h.show(*[f"{p}{n}" for n in fields], when=st == key)
    h.require(*[f"{p}{n}" for n in groups["employed"][:-1]], when=emp)
    h.require(*[f"{p}{n}" for n in groups["self_employed"]], when=se)
    h.require(f"{p}annual_pension", when=ret)
    for n in ("annual_salary", "annual_bonus", "annual_pension", "other_income"):
        h.number(f"{p}{n}", 0, 10_000_000)
    h.number(f"{p}profit_year1", -10_000_000, 10_000_000)
    h.number(f"{p}profit_year2", -10_000_000, 10_000_000)
    h.a_date(f"{p}employment_start", past=True)
    h.a_date(f"{p}trading_start", past=True)
    ts = h.date(f"{p}trading_start")
    if se and ts and not h.has_error(f"{p}trading_start") and (h.age(f"{p}trading_start") or 0) < 2:
        h.error(f"{p}trading_start", "We need at least 2 full years of trading")
    other = h.num(f"{p}other_income") or 0.0
    h.show(f"{p}other_income_source", when=other > 0)
    h.require(f"{p}other_income_source", when=other > 0)

    total = max(other, 0.0)
    if emp:
        total += max(h.num(f"{p}annual_salary") or 0.0, 0.0) + max(h.num(f"{p}annual_bonus") or 0.0, 0.0)
    elif se:
        total += max(((h.num(f"{p}profit_year1") or 0.0) + (h.num(f"{p}profit_year2") or 0.0)) / 2, 0.0)
    elif ret:
        total += max(h.num(f"{p}annual_pension") or 0.0, 0.0)
    return total


def rules(h) -> None:
    joint = h.id("applying_with") == "joint"
    h.show("tab_co", "acc_co", "co_relationship", "acc_income_co", when=joint)
    h.require("co_relationship", when=joint)
    _person_rules(h, "app_", True)
    _person_rules(h, "co_", joint)
    yearly = _income_rules(h, "app_", True) + _income_rules(h, "co_", joint)

    h.number("debt_count", 0, MAX_DEBTS, "Enter 0 to 6 debts", integer=True)
    k = h.repeat("debt_count", DEBTS, required=("_type", "_monthly", "_balance"))
    debts = 0.0
    for i in range(k):
        m = f"debt_{i + 1}_monthly"
        h.number(m, 0, 100_000)
        h.number(f"debt_{i + 1}_balance", 0, 10_000_000)
        if not h.on(f"debt_{i + 1}_cleared"):
            debts += max(h.num(m) or 0.0, 0.0)

    h.number("savings", 0, 100_000_000)
    h.number("investments", 0, 100_000_000)
    other = h.on("owns_other_property")
    h.show("other_property_value", "other_mortgage_balance", when=other)
    h.require("other_property_value", "other_mortgage_balance", when=other)
    gift = h.on("gifted_deposit") or h.id("deposit_source") == "gift"
    h.show("gifter_name", "gift_amount", "gift_letter", when=gift)
    h.require("gifter_name", "gift_amount", when=gift)
    h.number("gift_amount", 1, 10_000_000)

    h.match("property_postcode", r"[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}", "Enter a UK postcode, like SW1A 1AA")
    h.number("purchase_price", 10_000, 50_000_000)
    h.number("deposit", 0, 50_000_000)
    h.number("term_years", 5, 40, "Choose a term from 5 to 40 years", integer=True)
    price, dep, term = h.num("purchase_price"), h.num("deposit"), h.num("term_years")
    if price and dep is not None and price > 0 and not h.has_error("purchase_price") and not h.has_error("deposit"):
        if dep >= price:
            h.error("deposit", "The deposit must be less than the price")
        elif dep < MIN_DEPOSIT * price:
            h.error("deposit", f"The deposit must be at least 10% of the price ({MIN_DEPOSIT * price:,.0f} GBP)")
        loan = max(price - dep, 0.0)
        h.set("loan_amount", f"{loan:.0f}")
        h.set("ltv", f"{loan / price * 100:.1f}")
        if term and not h.has_error("term_years"):
            r, n = RATE / 12, int(term) * 12
            pay = loan * r if h.id("repayment_type") == "interest_only" else loan * r / (1 - (1 + r) ** -n)
            h.set("monthly_payment", f"{pay:.2f}")
            if yearly > 0:
                dti = (debts + pay) / (yearly / 12) * 100
                h.set("dti", f"{dti:.1f}")
                if dti > DTI_LIMIT:
                    h.error("dti", f"The ratio is {dti:.1f}%, above the 45% limit: borrow less, add a larger "
                                   "deposit, a longer term or clear some debts")
