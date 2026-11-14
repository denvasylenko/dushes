"""Lab form: a short-stay (Schengen-area) visa application at the Consulate of the Republic of Norland (big, 5 sequential tabs).

Rules: a minor (under 18) needs a parent or guardian and an uploaded parental consent; the employer fields appear
for employed, self-employed and student applicants; the passport must be issued within the last 10 years and expire at
least 3 months after the planned return; arrival is in the future, return on or after arrival, and the stay (the
read-only "Days of stay", arrival and return days included) is at most 90 days; the purpose shows its own section
(tourism: hotel, business: inviting company, family visit: host, other: details); the sponsor section appears when a
sponsor pays; funds must be at least 60 EUR per day of stay; travel insurance covers at least 30,000 EUR and the whole
stay; previous visas are a repeating group of up to 5 (count + numbered groups), each "to" after its "from"; a refusal
needs details. The tabs unlock one by one.
"""
from __future__ import annotations

from datetime import date

from ..dsl import C, F, opts

FORM_ID = "schengen_visa"
SEQUENTIAL = True

STATES = opts("norland:Republic of Norland", "valdoria:Valdoria", "eastmark:Eastmark", "lunesse:Lunesse",
              "brevia:Brevia", "ostrava_isles:Ostrava Isles")
MAX_PREV = 5


def _prev_group(i: int) -> list:
    p = f"prev_visa_{i}_"
    return [
        f"Previous visa {i}",
        F("Dropdown", p + "country", f"Visa {i}: issuing state", required=True, options=STATES),
        F("Input", p + "number", f"Visa {i}: visa sticker number", placeholder="NOR1234567"),
        F("DatePicker", p + "from", f"Visa {i}: valid from", required=True),
        F("DatePicker", p + "to", f"Visa {i}: valid to", required=True),
    ]


PREV_GROUPS = [[f"prev_visa_{i}_{s}" for s in ("country", "number", "from", "to")] for i in range(1, MAX_PREV + 1)]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_personal", "1. Personal details",
      C("Accordion", "acc_identity", "About you",
        F("Input", "surname", "Surname (family name)", required=True),
        F("Input", "surname_at_birth", "Surname at birth (if different)"),
        F("Input", "first_names", "First name(s)", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "birth_place", "Place of birth", required=True),
        F("Input", "birth_country", "Country of birth", required=True),
        F("Input", "nationality", "Current nationality", required=True),
        F("RadioGroup", "sex", "Sex", required=True, options=opts("female:Female", "male:Male", "other:Other")),
        F("Dropdown", "marital_status", "Marital status", required=True,
          options=opts("single:Single", "married:Married", "partnership:Registered partnership", "separated:Separated",
                       "divorced:Divorced", "widowed:Widowed")),
        F("FileUpload", "photo", "Passport photo (35 x 45 mm, taken in the last 6 months)", required=True)),
      C("Accordion", "acc_contact", "Home address and contact",
        F("Input", "home_address", "Street and number", required=True),
        F("Input", "home_postcode", "Postcode", required=True),
        F("Input", "home_city", "City", required=True),
        F("Input", "home_country", "Country of residence", required=True),
        F("Input", "phone", "Phone", required=True, placeholder="+44 7700 900123"),
        F("Input", "email", "Email", required=True)),
      C("Accordion", "acc_work", "Occupation",
        F("Dropdown", "occupation", "Current occupation", required=True,
          options=opts("employed:Employed", "self_employed:Self-employed", "student:Student", "retired:Retired",
                       "unemployed:Unemployed", "other:Other")),
        F("Input", "employer_name", "Employer, business or school", required=True),
        F("Input", "employer_address", "Its address and phone", required=True)),
      C("Accordion", "acc_guardian", "Parent or guardian (applicants under 18)",
        "Applicants under 18 need a parent or guardian and a signed parental consent.",
        F("Input", "guardian_name", "Parent or guardian's full name", required=True),
        F("Dropdown", "guardian_relation", "Relationship", required=True,
          options=opts("mother:Mother", "father:Father", "legal:Legal guardian")),
        F("Input", "guardian_address", "Parent or guardian's address", required=True),
        F("Input", "guardian_phone", "Parent or guardian's phone", required=True),
        F("FileUpload", "parental_consent", "Parental consent signed by both parents", required=True))),
    C("Tab", "tab_passport", "2. Passport",
      C("Accordion", "acc_passport", "Travel document",
        "The passport must be issued within the last 10 years and stay valid at least 3 months after your return.",
        F("Dropdown", "passport_type", "Type of travel document", required=True,
          options=opts("ordinary:Ordinary passport", "diplomatic:Diplomatic passport", "service:Service passport",
                       "official:Official passport", "other:Other travel document")),
        F("Input", "passport_number", "Passport number", required=True, placeholder="AB1234567"),
        F("Input", "passport_issued_by", "Issued by (country)", required=True),
        F("DatePicker", "passport_issue_date", "Date of issue", required=True),
        F("DatePicker", "passport_expiry_date", "Valid until", required=True),
        F("Input", "national_id_number", "National identity number (if any)")),
      C("Accordion", "acc_residence", "Residence in another country",
        F("Checkbox", "resides_elsewhere", "I live in a country that is not my country of nationality"),
        F("Input", "residence_permit_number", "Residence permit number", required=True),
        F("DatePicker", "residence_permit_expiry", "Residence permit valid until", required=True))),
    C("Tab", "tab_travel", "3. Travel",
      C("Accordion", "acc_trip", "The trip",
        "A short-stay visa covers at most 90 days.",
        F("Dropdown", "main_destination", "Main destination", required=True, options=STATES),
        F("MultiSelect", "other_destinations", "Other states you will visit", options=STATES),
        F("Dropdown", "first_entry", "State of first entry", required=True, options=STATES),
        F("Dropdown", "purpose", "Main purpose of the journey", required=True,
          options=opts("tourism:Tourism", "business:Business", "family:Visiting family or friends", "other:Other")),
        F("TextArea", "purpose_details", "Describe the purpose", required=True),
        F("RadioGroup", "entries", "Number of entries", required=True,
          options=opts("single:Single entry", "double:Two entries", "multiple:Multiple entries")),
        F("DatePicker", "arrival_date", "Planned arrival", required=True),
        F("DatePicker", "departure_date", "Planned return", required=True),
        F("Input", "days_of_stay", "Days of stay (calculated)", readonly=True),
        F("Dropdown", "transport", "Means of transport", options=opts("air:Air", "train:Train", "car:Car", "bus:Coach", "sea:Sea"))),
      C("Accordion", "acc_hotel", "Accommodation (tourism)",
        F("Input", "hotel_name", "Hotel or rental name", required=True),
        F("Input", "hotel_address", "Hotel address", required=True),
        F("Input", "hotel_phone", "Hotel phone"),
        F("Input", "hotel_booking_ref", "Booking reference")),
      C("Accordion", "acc_company", "Inviting company (business)",
        F("Input", "company_name", "Company name", required=True),
        F("Input", "company_address", "Company address", required=True),
        F("Input", "company_phone", "Company phone", required=True),
        F("Input", "company_contact", "Contact person"),
        F("Input", "company_email", "Contact email"),
        F("FileUpload", "invitation_letter", "Invitation letter from the company", required=True)),
      C("Accordion", "acc_host", "Host (family or friends visit)",
        F("Input", "host_surname", "Host's surname", required=True),
        F("Input", "host_first_name", "Host's first name", required=True),
        F("DatePicker", "host_birth_date", "Host's date of birth"),
        F("Input", "host_address", "Host's address", required=True),
        F("Input", "host_phone", "Host's phone", required=True),
        F("Input", "host_email", "Host's email"),
        F("Dropdown", "host_relation", "Your relationship to the host", required=True,
          options=opts("spouse:Spouse or partner", "child:Child", "parent:Parent", "sibling:Brother or sister",
                       "relative:Other relative", "friend:Friend")),
        F("Dropdown", "host_status", "Host's status", options=opts("citizen:Citizen", "resident:Resident", "other:Other")),
        F("FileUpload", "host_invitation", "Host's signed invitation"))),
    C("Tab", "tab_funds", "4. Costs and insurance",
      C("Accordion", "acc_costs", "Who pays for the trip",
        "You need at least 60 EUR for each day of stay.",
        F("RadioGroup", "costs_covered_by", "Costs are covered by", required=True,
          options=opts("self:Myself", "sponsor:A sponsor", "both:Myself and a sponsor")),
        F("MultiSelect", "means_of_support", "My means of support",
          options=opts("cash:Cash", "card:Credit card", "accommodation:Prepaid accommodation",
                       "transport:Prepaid transport", "other:Other")),
        F("NumberInput", "funds_amount", "Funds available for the trip, EUR", required=True)),
      C("Accordion", "acc_sponsor", "Sponsor",
        F("Input", "sponsor_name", "Sponsor's full name or company", required=True),
        F("Dropdown", "sponsor_relation", "Sponsor is", required=True,
          options=opts("host:My host", "company:The inviting company", "relative:A relative", "other:Someone else")),
        F("Input", "sponsor_address", "Sponsor's address", required=True),
        F("Input", "sponsor_phone", "Sponsor's phone", required=True),
        F("Input", "sponsor_email", "Sponsor's email"),
        F("MultiSelect", "sponsor_means", "What the sponsor covers",
          options=opts("all:All costs", "accommodation:Accommodation", "transport:Transport", "cash:Cash allowance")),
        F("FileUpload", "sponsor_letter", "Sponsor's letter of guarantee", required=True)),
      C("Accordion", "acc_insurance", "Travel medical insurance",
        "Insurance must cover at least 30,000 EUR and the whole stay.",
        F("Input", "insurance_company", "Insurer", required=True),
        F("Input", "insurance_policy", "Policy number", required=True),
        F("NumberInput", "insurance_cover", "Cover, EUR", required=True),
        F("DatePicker", "insurance_from", "Insured from", required=True),
        F("DatePicker", "insurance_to", "Insured until", required=True),
        F("FileUpload", "insurance_doc", "Insurance certificate", required=True))),
    C("Tab", "tab_previous", "5. Previous visas",
      C("Accordion", "acc_prev", "Visas in the last 3 years",
        F("Checkbox", "fingerprints_before", "My fingerprints were taken for an earlier visa"),
        F("DatePicker", "fingerprints_date", "When were they taken?", required=True),
        F("NumberInput", "prev_visa_count", "Number of visas in the last 3 years (0 to 5)"),
        *[x for i in range(1, MAX_PREV + 1) for x in _prev_group(i)]),
      C("Accordion", "acc_declaration", "Declaration",
        F("Checkbox", "refused_before", "I have been refused a visa before"),
        F("TextArea", "refusal_details", "When, by which state and why?", required=True),
        F("Checkbox", "declaration", "I declare that all the information I gave is correct and complete", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Short-stay visa application",
    "starters": ["I want a tourist visa for 2 weeks", "Apply for a business visa", "My son is 15, can he apply?"],
    "persona": "You are the visa section assistant of the Consulate of the Republic of Norland. Be precise and neutral; "
               "never promise that a visa will be granted.",
    "flow_hints": [
        "The tabs unlock one by one: personal details, passport, travel, costs and insurance, previous visas.",
        "Applicants under 18 need a parent or guardian and an uploaded parental consent.",
        "Ask the purpose early: it decides which section follows (hotel, inviting company or host).",
        "Ask how many visas the applicant had in the last 3 years, then each one in turn (up to 5).",
    ],
    "glossary": {
        "days_of_stay": "Calculated from arrival to return, both days included. A short-stay visa covers at most 90 days.",
        "passport_expiry_date": "The passport must be valid at least 3 months after the planned return and issued in the last 10 years.",
        "funds_amount": "At least 60 EUR for each day of stay.",
        "insurance_cover": "At least 30,000 EUR, valid for the whole stay.",
        "prev_visa_count": "Visas issued in the last 3 years, at most 5 can be listed.",
        "fee": "The visa fee is 90 EUR; children aged 6 to 11 pay 45 EUR; children under 6 are free.",
    },
    "pii": ["surname", "first_names", "birth_date", "phone", "email", "home_address", "passport_number",
            "national_id_number", "guardian_phone", "host_phone", "sponsor_phone"],
}

PAGE = {
    "path": "/lab/norland-visa",
    "title": "Consulate of the Republic of Norland: short-stay visa",
    "description": "Apply for a short-stay (up to 90 days) visa at the Consulate of the Republic of Norland.",
    "keywords": ["visa", "schengen", "consulate", "travel", "norland", "short stay", "tourist visa"],
    "sections": [
        {"id": "rules", "title": "Who can apply",
         "text": "A short-stay visa covers at most 90 days. Your passport must be issued within the last 10 years and stay "
                 "valid at least 3 months after your planned return. You need at least 60 EUR for each day of stay and "
                 "travel medical insurance of at least 30,000 EUR for the whole stay. Applicants under 18 need a parental "
                 "consent signed by both parents."},
        {"id": "fees", "title": "Fees",
         "text": "The visa fee is 90 EUR. Children aged 6 to 11 pay 45 EUR. Children under 6 are free. "
                 "The fee is paid at the appointment."},
    ],
}


def _add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    y, mo = d.year + y, mo + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, mo, day)
        except ValueError:
            continue
    return d


def rules(h) -> None:
    today = date.today()
    # personal
    h.a_date("birth_date", past=True)
    age = h.age("birth_date")
    minor = age is not None and age < 18
    g = ["guardian_name", "guardian_relation", "guardian_address", "guardian_phone", "parental_consent"]
    h.show("acc_guardian", *g, when=minor)
    h.require(*g, when=minor)
    h.phone("phone")
    h.phone("guardian_phone")
    h.email("email")
    works = h.id("occupation") in ("employed", "self_employed", "student")
    h.show("employer_name", "employer_address", when=works)
    h.require("employer_name", "employer_address", when=works)

    # passport
    h.match("passport_number", r"[A-Za-z0-9]{6,9}", "A passport number has 6 to 9 letters or digits")
    h.a_date("passport_issue_date", past=True)
    iss = h.date("passport_issue_date")
    if iss and iss < _add_months(today, -120):
        h.error("passport_issue_date", "The passport must be issued within the last 10 years")
    other = h.on("resides_elsewhere")
    h.show("residence_permit_number", "residence_permit_expiry", when=other)
    h.require("residence_permit_number", "residence_permit_expiry", when=other)
    h.a_date("residence_permit_expiry", future=True, msg="The residence permit has expired")

    # travel
    arr, dep = h.date("arrival_date"), h.date("departure_date")
    h.a_date("arrival_date", future=True, msg="The arrival must be in the future")
    days = None
    if arr and dep:
        if dep < arr:
            h.error("departure_date", "The return must be on or after the arrival")
        else:
            days = (dep - arr).days + 1
            if days > 90:
                h.error("departure_date", f"A stay is at most 90 days (this one is {days}); return earlier")
    h.set("days_of_stay", str(days) if days else "")
    exp = h.date("passport_expiry_date")
    h.a_date("passport_expiry_date", future=True, msg="This passport has expired")
    if exp and dep and exp < _add_months(dep, 3) and not h.has_error("passport_expiry_date"):
        h.error("passport_expiry_date", "The passport must be valid at least 3 months after your return; renew it first")

    purpose = h.id("purpose")
    sections = {
        "tourism": ("acc_hotel", ["hotel_name", "hotel_address"], ["hotel_phone", "hotel_booking_ref"]),
        "business": ("acc_company", ["company_name", "company_address", "company_phone", "invitation_letter"],
                     ["company_contact", "company_email"]),
        "family": ("acc_host", ["host_surname", "host_first_name", "host_address", "host_phone", "host_relation"],
                   ["host_birth_date", "host_email", "host_status", "host_invitation"]),
    }
    for key, (acc, req, opt) in sections.items():
        on = purpose == key
        h.show(acc, *req, *opt, when=on)
        h.require(*req, when=on)
    h.show("purpose_details", when=purpose == "other")
    h.require("purpose_details", when=purpose == "other")
    h.phone("hotel_phone")
    h.phone("company_phone")
    h.phone("host_phone")
    h.email("company_email")
    h.email("host_email")
    h.a_date("host_birth_date", past=True)

    # costs and insurance
    sp = h.id("costs_covered_by") in ("sponsor", "both")
    s_req = ["sponsor_name", "sponsor_relation", "sponsor_address", "sponsor_phone", "sponsor_letter"]
    h.show("acc_sponsor", *s_req, "sponsor_email", "sponsor_means", when=sp)
    h.require(*s_req, when=sp)
    h.phone("sponsor_phone")
    h.email("sponsor_email")
    h.number("funds_amount", lo=0)
    f = h.num("funds_amount")
    if f is not None and days and f < 60 * days and not h.has_error("funds_amount"):
        h.error("funds_amount", f"You need at least {60 * days} EUR for {days} days (60 EUR a day)")
    h.number("insurance_cover", lo=30000, msg="The cover must be at least 30,000 EUR")
    i_from, i_to = h.date("insurance_from"), h.date("insurance_to")
    if i_from and arr and i_from > arr:
        h.error("insurance_from", "The insurance must start on or before your arrival")
    if i_to and dep and i_to < dep:
        h.error("insurance_to", "The insurance must last until your return")
    if i_from and i_to and i_to < i_from:
        h.error("insurance_to", "The end must be after the start")

    # previous visas
    fp = h.on("fingerprints_before")
    h.show("fingerprints_date", when=fp)
    h.require("fingerprints_date", when=fp)
    h.a_date("fingerprints_date", past=True)
    h.number("prev_visa_count", lo=0, hi=MAX_PREV, integer=True, msg="Enter 0 to 5 (list the 5 most recent)")
    k = h.repeat("prev_visa_count", PREV_GROUPS, required=("_country", "_from", "_to"))
    for i in range(1, k + 1):
        p = f"prev_visa_{i}_"
        h.match(p + "number", r"[A-Za-z0-9]{6,12}", "A visa sticker number has 6 to 12 letters or digits")
        a, b = h.date(p + "from"), h.date(p + "to")
        h.a_date(p + "from", past=True)
        if a and b and b <= a:
            h.error(p + "to", "The end date must be after the start date")
    ref = h.on("refused_before")
    h.show("refusal_details", when=ref)
    h.require("refusal_details", when=ref)

