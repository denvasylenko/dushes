"""Demo form 1: a large loan application.

Not part of the agent: it plays the role of the form backend.
"""
from __future__ import annotations

from .dsl import C, F, N, base_props, initial_state, opts, to_jsx  # noqa: F401

YES_NO_COUNT = opts("0:None", "1:1", "2:2", "3:3")

REGIONS = opts("msk:Moscow", "spb:Saint Petersburg", "kzn:Republic of Tatarstan",
               "nsk:Novosibirsk Region", "svr:Sverdlovsk Region", "krd:Krasnodar Territory")

CITIES = {
    "msk": opts("msk_c:Moscow", "zel:Zelenograd", "trk:Troitsk"),
    "spb": opts("spb_c:Saint Petersburg", "kln:Kolpino", "pshk:Pushkin", "krn:Kronstadt"),
    "kzn": opts("kzn_c:Kazan", "nch:Naberezhnye Chelny", "alm:Almetyevsk", "nkm:Nizhnekamsk"),
    "nsk": opts("nsk_c:Novosibirsk", "brd:Berdsk", "isk:Iskitim"),
    "svr": opts("ekb:Yekaterinburg", "ntg:Nizhny Tagil", "kmn:Kamensk-Uralsky"),
    "krd": opts("krd_c:Krasnodar", "soc:Sochi", "nvr:Novorossiysk", "arm:Armavir", "anp:Anapa"),
}

CAR_MODELS = {
    "lada": opts("vesta:Vesta", "granta:Granta", "niva:Niva Travel", "largus:Largus"),
    "kia": opts("rio:Rio", "ceed:Ceed", "sportage:Sportage", "k5:K5"),
    "toyota": opts("camry:Camry", "corolla:Corolla", "rav4:RAV4", "lc:Land Cruiser"),
    "haval": opts("jolion:Jolion", "f7:F7", "h9:H9"),
    "geely": opts("coolray:Coolray", "monjaro:Monjaro", "atlas:Atlas"),
}

LOAN_PURPOSES = {
    "consumer": opts("repair:Home renovation", "edu:Education", "med:Medical treatment", "travel:Travel", "other:Other"),
    "mortgage": opts("flat_new:New-build apartment", "flat_sec:Resale apartment",
                     "house:House with land", "land:Land plot"),
    "auto": opts("car_new:New car", "car_used:Used car"),
    "refinance": opts("refi_one:One loan", "refi_many:Several loans"),
}

LOAN_TERMS = {
    "consumer": opts("12:12 months", "24:24 months", "36:36 months", "60:60 months"),
    "mortgage": opts("120:10 years", "180:15 years", "240:20 years", "300:25 years", "360:30 years"),
    "auto": opts("12:12 months", "36:36 months", "60:60 months", "84:84 months"),
    "refinance": opts("24:24 months", "36:36 months", "60:60 months", "84:84 months"),
}

LOAN_RATES = {"consumer": 21.9, "mortgage": 16.5, "auto": 18.9, "refinance": 19.5}


def person_fields(p: str, req: bool = True) -> list[N]:
    return [
        F("Input", f"{p}last_name", "Last name", required=req, placeholder="As in your passport"),
        F("Input", f"{p}first_name", "First name", required=req),
        F("Input", f"{p}middle_name", "Middle name"),
        F("DatePicker", f"{p}birth_date", "Date of birth", required=req),
        F("Input", f"{p}age", "Age (calculated)", readonly=True),
        F("Dropdown", f"{p}gender", "Gender", required=req, options=opts("m:Male", "f:Female")),
        F("Input", f"{p}birth_place", "Place of birth", required=req),
    ]


def passport_fields(p: str) -> list[N]:
    return [
        F("Input", f"{p}passport_series", "Passport series", required=True, placeholder="4 digits"),
        F("Input", f"{p}passport_number", "Passport number", required=True, placeholder="6 digits"),
        F("DatePicker", f"{p}passport_issued_date", "Date of issue", required=True),
        F("Input", f"{p}passport_issued_by", "Issued by", required=True),
        F("Input", f"{p}passport_dept_code", "Department code", required=True, placeholder="000-000"),
    ]


def address_fields(p: str, req: bool = True) -> list[N]:
    return [
        F("Dropdown", f"{p}region", "Region", required=req, options=REGIONS),
        F("Dropdown", f"{p}city", "City", required=req, options=[]),
        F("Input", f"{p}street", "Street", required=req),
        F("Input", f"{p}house", "Building", required=req),
        F("Input", f"{p}flat", "Apartment"),
        F("Input", f"{p}zip", "Postal code", placeholder="6 digits"),
    ]


def realty_slot(i: int) -> N:
    p = f"asset_realty_{i}_"
    return C("Accordion", f"asset_realty_{i}", f"Property #{i}",
             F("Dropdown", f"{p}type", "Property type", required=True,
               options=opts("flat:Apartment", "house:House", "land:Land plot", "comm:Commercial")),
             F("Dropdown", f"{p}region", "Region", required=True, options=REGIONS),
             F("Input", f"{p}address", "Address", required=True),
             F("NumberInput", f"{p}area", "Area, m²", required=True),
             F("NumberInput", f"{p}value", "Estimated value, ₽", required=True),
             F("Dropdown", f"{p}ownership", "Ownership", required=True,
               options=opts("full:Sole", "share:Shared", "joint:Joint")),
             F("NumberInput", f"{p}share", "Share, %"),
             F("Checkbox", f"{p}encumbered", "Encumbered (pledged)"))


def vehicle_slot(i: int) -> N:
    p = f"asset_vehicle_{i}_"
    return C("Accordion", f"asset_vehicle_{i}", f"Vehicle #{i}",
             F("Input", f"{p}brand", "Make", required=True),
             F("Input", f"{p}model", "Model", required=True),
             F("NumberInput", f"{p}year", "Year of manufacture", required=True),
             F("Input", f"{p}vin", "VIN", placeholder="17 characters"),
             F("NumberInput", f"{p}value", "Market value, ₽", required=True),
             F("Checkbox", f"{p}encumbered", "Pledged"))


def account_slot(i: int) -> N:
    p = f"asset_account_{i}_"
    return C("Accordion", f"asset_account_{i}", f"Account / deposit #{i}",
             F("Input", f"{p}bank", "Bank", required=True),
             F("Dropdown", f"{p}type", "Type", required=True,
               options=opts("current:Current account", "deposit:Deposit", "broker:Brokerage account")),
             F("NumberInput", f"{p}balance", "Balance, ₽", required=True),
             F("Dropdown", f"{p}currency", "Currency", options=opts("rub:RUB", "usd:USD", "eur:EUR", "cny:CNY")))


def liability_slot(i: int) -> N:
    p = f"liability_{i}_"
    return C("Accordion", f"liability_{i}", f"Existing loan #{i}",
             F("Input", f"{p}bank", "Lender", required=True),
             F("Dropdown", f"{p}type", "Loan type", required=True,
               options=opts("consumer:Consumer loan", "mortgage:Mortgage", "auto:Car loan", "card:Credit card")),
             F("NumberInput", f"{p}balance", "Outstanding balance, ₽", required=True),
             F("NumberInput", f"{p}monthly", "Monthly payment, ₽", required=True),
             F("DatePicker", f"{p}end_date", "Maturity date"),
             F("Checkbox", f"{p}refinance", "Refinance in this application"),
             F("Checkbox", f"{p}overdue", "Had late payments"))


FORM = C(
    "Tabs", "main", None,
    # ---------------------------------------------------------- 1. Applicant
    C("Tab", "tab_applicant", "Applicant",
      C("Accordion", "acc_personal", "Personal details", *person_fields("")),
      C("Accordion", "acc_passport", "Passport", *passport_fields(""),
        F("Input", "inn", "Tax ID (INN)", placeholder="12 digits"),
        F("Input", "snils", "Social insurance number (SNILS)", placeholder="000-000-000 00")),
      C("Accordion", "acc_addresses", "Addresses",
        C("Tabs", "address_tabs", None,
          C("Tab", "tab_addr_reg", "Registered address", *address_fields("reg_"),
            F("DatePicker", "reg_since", "Registered since", required=True)),
          C("Tab", "tab_addr_fact", "Actual residence",
            F("Checkbox", "fact_same_as_reg", "Same as registered address"),
            *address_fields("fact_"),
            F("Dropdown", "fact_housing_type", "Housing type", required=True,
              options=opts("own:Own", "rent:Rented", "relatives:With relatives", "service:Employer-provided")),
            F("NumberInput", "fact_rent_amount", "Monthly rent, ₽", required=True)))),
      C("Accordion", "acc_contacts", "Contacts",
        F("Input", "phone_mobile", "Mobile phone", required=True, placeholder="+7XXXXXXXXXX"),
        F("Input", "phone_home", "Home phone"),
        F("Input", "email", "Email", required=True),
        F("Dropdown", "contact_time", "Preferred time for a call",
          options=opts("morning:9:00–12:00", "day:12:00–18:00", "evening:18:00–21:00")),
        F("Checkbox", "contact_messenger", "Messaging apps are fine")),
      C("Accordion", "acc_education", "Education",
        F("Dropdown", "education_level", "Education level", required=True,
          options=opts("school:Secondary", "college:Vocational", "bachelor:Bachelor's degree",
                       "master:Master's degree", "phd:Doctorate")),
        F("Input", "education_institution", "Institution"),
        F("NumberInput", "education_year", "Graduation year"))),
    # ---------------------------------------------------------- 2. Family
    C("Tab", "tab_family", "Family",
      C("Accordion", "acc_marital", "Marital status",
        F("Dropdown", "marital_status", "Marital status", required=True,
          options=opts("single:Single", "married:Married",
                       "divorced:Divorced", "widowed:Widowed", "civil:Civil partnership")),
        F("Checkbox", "marriage_contract", "Prenuptial agreement"),
        F("NumberInput", "dependents_count", "Number of dependants")),
      C("Accordion", "acc_spouse", "Spouse", *person_fields("spouse_"),
        F("Dropdown", "spouse_employment", "Spouse's employment", required=True,
          options=opts("employed:Employed", "unemployed:Not employed", "pensioner:Retired")),
        F("NumberInput", "spouse_income", "Spouse's income, ₽/month")),
      C("Accordion", "acc_children", "Children",
        F("Dropdown", "children_count", "Children under 18", required=True, options=YES_NO_COUNT),
        *[F("DatePicker", f"child_{i}_birth_date", f"Child #{i} date of birth", required=True) for i in (1, 2, 3)])),
    # ---------------------------------------------------------- 3. Employment & income
    C("Tab", "tab_employment", "Employment & income",
      C("Accordion", "acc_employment_type", "Employment type",
        F("Dropdown", "employment_type", "Employment type", required=True,
          options=opts("employee:Employed", "business:Sole proprietor",
                       "pensioner:Retired", "unemployed:Not working"))),
      C("Accordion", "acc_employer", "Employer",
        F("Input", "employer_name", "Company name", required=True),
        F("Input", "employer_inn", "Company tax ID", required=True, placeholder="10 digits"),
        F("Dropdown", "employer_industry", "Industry", required=True,
          options=opts("it:IT", "trade:Retail", "industry:Manufacturing", "gov:Public sector",
                       "finance:Finance", "medicine:Healthcare", "education:Education", "other:Other")),
        F("Input", "employer_position", "Position", required=True),
        F("DatePicker", "employer_since", "Employed since", required=True),
        F("Input", "employer_phone", "Work phone", required=True, placeholder="+7XXXXXXXXXX"),
        F("Input", "employer_address", "Company address")),
      C("Accordion", "acc_business", "Sole proprietor",
        F("Input", "business_ogrnip", "Business registration number (OGRNIP)", required=True, placeholder="15 digits"),
        F("DatePicker", "business_reg_date", "Business registration date", required=True),
        F("Dropdown", "business_tax", "Tax regime", required=True,
          options=opts("usn6:Simplified 6%", "usn15:Simplified 15%", "osno:General regime", "patent:Patent", "npd:Self-employed tax")),
        F("Input", "business_activity", "Main activity", required=True),
        F("NumberInput", "business_employees", "Number of employees")),
      C("Accordion", "acc_pension", "Pension",
        F("Dropdown", "pension_type", "Pension type", required=True,
          options=opts("age:Old-age", "disability:Disability", "service:Long service")),
        F("Input", "pension_certificate", "Pension certificate number")),
      C("Accordion", "acc_income", "Income",
        C("Tabs", "income_tabs", None,
          C("Tab", "tab_income_main", "Main income",
            F("NumberInput", "income_main", "Main income, ₽/month", required=True),
            F("Dropdown", "income_proof_type", "Proof of income", required=True,
              options=opts("2ndfl:2-NDFL tax certificate", "bank:Bank's income form", "sfr:Pension fund (SFR) statement", "none:No proof"))),
          C("Tab", "tab_income_extra", "Additional income",
            F("Checkbox", "has_extra_income", "I have additional income"),
            F("NumberInput", "extra_income_amount", "Additional income, ₽/month", required=True),
            F("Dropdown", "extra_income_source", "Source", required=True,
              options=opts("rent:Rental income", "freelance:Side work", "invest:Investments", "other:Other"))),
          C("Tab", "tab_expenses", "Expenses",
            F("NumberInput", "expenses_monthly", "Fixed expenses, ₽/month", required=True),
            F("NumberInput", "expenses_utilities", "Utilities, ₽/month"),
            F("Input", "pdn_ratio", "Debt-to-income ratio (calculated)", readonly=True))))),
    # ---------------------------------------------------------- 4. Loan
    C("Tab", "tab_loan", "Loan",
      C("Accordion", "acc_loan_params", "Loan details",
        F("Dropdown", "loan_type", "Loan type", required=True,
          options=opts("consumer:Consumer loan", "mortgage:Mortgage", "auto:Car loan", "refinance:Refinancing")),
        F("Dropdown", "loan_purpose", "Loan purpose", required=True, options=[]),
        F("NumberInput", "loan_amount", "Loan amount, ₽", required=True),
        F("Dropdown", "loan_term", "Loan term", required=True, options=[]),
        F("Input", "loan_rate", "Interest rate, % per year", readonly=True),
        F("Input", "monthly_payment", "Monthly payment, ₽ (calculated)", readonly=True),
        F("NumberInput", "down_payment", "Down payment, ₽", required=True)),
      C("Accordion", "acc_loan_options", "Extras",
        F("Checkbox", "opt_life_insurance", "Life insurance"),
        F("Dropdown", "opt_insurance_company", "Insurance company", required=True,
          options=opts("ins_a:Insurer A", "ins_b:Insurer B", "ins_c:Insurer C")),
        F("Checkbox", "opt_sms", "SMS notifications"),
        F("Dropdown", "payout_method", "Payout method", required=True,
          options=opts("card:To a card of this bank", "account:To an account in another bank", "cash:Cash at a branch")),
        F("Input", "payout_account", "Account number for the transfer", required=True, placeholder="20 digits"),
        F("Input", "payout_bik", "Recipient bank BIC", required=True, placeholder="9 digits")),
      C("Accordion", "acc_refinance", "Refinancing",
        "List the loans you want to move to us. Their details go on the \"Assets & liabilities\" tab.",
        F("NumberInput", "refi_total", "Total amount to refinance, ₽", required=True),
        F("Checkbox", "refi_extra_cash", "I need extra cash on top of refinancing"),
        F("NumberInput", "refi_extra_amount", "Extra amount, ₽", required=True))),
    # ---------------------------------------------------------- 5. Collateral
    C("Tab", "tab_collateral", "Collateral",
      C("Tabs", "collateral_tabs", None,
        C("Tab", "tab_collateral_realty", "Real estate",
          C("Accordion", "acc_collateral_object", "Pledged property",
            F("Dropdown", "col_realty_type", "Property type", required=True,
              options=opts("flat:Apartment", "house:House", "townhouse:Townhouse", "land:Land plot")),
            F("Dropdown", "col_realty_market", "Market", required=True,
              options=opts("new:New build", "secondary:Resale")),
            F("Dropdown", "col_realty_region", "Region", required=True, options=REGIONS),
            F("Dropdown", "col_realty_city", "City", required=True, options=[]),
            F("Input", "col_realty_address", "Property address", required=True),
            F("NumberInput", "col_realty_area", "Area, m²", required=True),
            F("NumberInput", "col_realty_rooms", "Rooms"),
            F("NumberInput", "col_realty_floor", "Floor"),
            F("NumberInput", "col_realty_price", "Property price, ₽", required=True)),
          C("Accordion", "acc_collateral_developer", "Developer",
            F("Input", "col_dev_name", "Developer name", required=True),
            F("Input", "col_dev_complex", "Housing complex", required=True),
            F("DatePicker", "col_dev_deadline", "Completion date", required=True)),
          C("Accordion", "acc_collateral_seller", "Seller",
            F("Dropdown", "col_seller_type", "Seller", required=True,
              options=opts("person:Individual", "company:Company")),
            F("Input", "col_seller_name", "Seller's name", required=True),
            F("Checkbox", "col_seller_minor_owners", "Some owners are minors"))),
        C("Tab", "tab_collateral_auto", "Car",
          C("Accordion", "acc_collateral_car", "Car",
            F("Dropdown", "col_car_brand", "Make", required=True,
              options=opts("lada:LADA", "kia:Kia", "toyota:Toyota", "haval:Haval", "geely:Geely")),
            F("Dropdown", "col_car_model", "Model", required=True, options=[]),
            F("NumberInput", "col_car_year", "Year of manufacture", required=True),
            F("Input", "col_car_vin", "VIN", required=True, placeholder="17 characters"),
            F("NumberInput", "col_car_mileage", "Mileage, km", required=True),
            F("NumberInput", "col_car_price", "Car price, ₽", required=True)),
          C("Accordion", "acc_collateral_dealer", "Dealership",
            F("Input", "col_dealer_name", "Dealership name", required=True),
            F("Input", "col_dealer_inn", "Dealership tax ID", placeholder="10 digits"))))),
    # ---------------------------------------------------------- 6. Co-borrower
    C("Tab", "tab_coborrower", "Co-borrower",
      C("Accordion", "acc_cob_flag", "Co-borrower",
        F("Checkbox", "has_coborrower", "Add a co-borrower"),
        F("Dropdown", "cob_relation", "Relationship", required=True,
          options=opts("spouse:Spouse", "parent:Parent", "child:Child", "other:Other"))),
      C("Accordion", "acc_cob_person", "Co-borrower details", *person_fields("cob_")),
      C("Accordion", "acc_cob_passport", "Co-borrower's passport", *passport_fields("cob_")),
      C("Accordion", "acc_cob_income", "Co-borrower's income",
        F("NumberInput", "cob_income", "Income, ₽/month", required=True),
        F("Input", "cob_employer", "Employer", required=True))),
    # ---------------------------------------------------------- 7. Assets & liabilities
    C("Tab", "tab_assets", "Assets & liabilities",
      C("Tabs", "assets_tabs", None,
        C("Tab", "tab_assets_realty", "Real estate",
          F("Dropdown", "asset_realty_count", "How many properties do you own", required=True,
            options=YES_NO_COUNT),
          *[realty_slot(i) for i in (1, 2, 3)]),
        C("Tab", "tab_assets_vehicles", "Vehicles",
          F("Dropdown", "asset_vehicle_count", "How many vehicles", required=True, options=YES_NO_COUNT),
          *[vehicle_slot(i) for i in (1, 2, 3)]),
        C("Tab", "tab_assets_accounts", "Accounts & deposits",
          F("Dropdown", "asset_account_count", "How many accounts and deposits to list", required=True, options=YES_NO_COUNT),
          *[account_slot(i) for i in (1, 2, 3)]),
        C("Tab", "tab_liabilities", "Existing loans",
          F("Dropdown", "liability_count", "How many existing loans", required=True, options=YES_NO_COUNT),
          *[liability_slot(i) for i in (1, 2, 3)],
          F("Input", "liabilities_total_monthly", "Total loan payments, ₽/month (calculated)", readonly=True)))),
    # ---------------------------------------------------------- 8. Documents & consents
    C("Tab", "tab_documents", "Documents & consents",
      C("Accordion", "acc_docs", "Documents",
        "Upload scans or photos. Accepted formats: PDF, JPG, PNG.",
        F("FileUpload", "doc_passport", "Passport (all pages with stamps)", required=True),
        F("FileUpload", "doc_income", "Proof of income", required=True),
        F("FileUpload", "doc_employment", "Employment record (STD-R)"),
        F("FileUpload", "doc_collateral", "Documents for the pledged property", required=True),
        F("FileUpload", "doc_marriage", "Marriage certificate", required=True)),
      C("Accordion", "acc_consents", "Consents",
        F("Checkbox", "consent_pd", "Consent to personal data processing", required=True),
        F("Checkbox", "consent_bki", "Consent to a credit bureau check", required=True),
        F("Checkbox", "consent_marketing", "Consent to marketing offers"),
        F("Input", "codeword", "Code word", required=True, placeholder="Used to identify you by phone"))),
)



FORM_JSX = to_jsx(FORM)
BASE_PROPS = base_props(FORM)
INITIAL_STATE = initial_state(FORM)
