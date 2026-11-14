"""Lab form: enrolment at a primary school in Krakow (Polish formats: PESEL with its checksum, NN-NNN postcodes, +48).

Rules: the child's PESEL is 11 digits with a valid checksum, and the birth date must match the date coded in it;
the child is 6 to 15 years old at the start of the school year (1 September); postcodes are NN-NNN; phones are
+48 and 9 digits; the second parent or guardian is optional (a checkbox shows and requires their fields);
siblings at the school are a repeating group of up to 3; medical details appear with "medical needs";
at most 2 after-school clubs (an error otherwise); the gluten-free lunch needs the medical note; the bus stop
appears for the school bus; "walks home alone" is only for children aged 10 or more; photo consent is required.
"""
from __future__ import annotations

from datetime import date

from ..dsl import C, F, opts

FORM_ID = "school_enrollment"

MAX_SIBLINGS = 3
MAX_CLUBS = 2
PHONE_RX = r"\+48\s?\d{3}\s?\d{3}\s?\d{3}"
PHONE_MSG = "A Polish phone is +48 and 9 digits, like +48 512 345 678"
POST_RX = r"\d{2}-\d{3}"
POST_MSG = "A postcode looks like 30-001"
GRADES = opts(*[f"{g}:Grade {g}" for g in range(1, 9)])


def pesel_ok(v: str) -> bool:
    if len(v) != 11 or not v.isdigit():
        return False
    w = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    return (10 - sum(int(c) * k for c, k in zip(v, w)) % 10) % 10 == int(v[10])


def pesel_birth(v: str) -> date | None:
    """The birth date coded in a PESEL (months +20 for 2000-2099, +80 for 1800s)."""
    yy, mm, dd = int(v[0:2]), int(v[2:4]), int(v[4:6])
    century = {0: 1900, 20: 2000, 40: 2100, 60: 2200, 80: 1800}.get(mm // 20 * 20)
    if century is None:
        return None
    try:
        return date(century + yy, mm % 20, dd)
    except ValueError:
        return None


def _parent(i: int, title: str) -> list:
    return [F("Input", f"parent_{i}_name", f"{title}: full name", required=True),
            F("Dropdown", f"parent_{i}_relation", f"{title}: relationship", required=True,
              options=opts("mother:Mother", "father:Father", "guardian:Legal guardian")),
            F("Input", f"parent_{i}_phone", f"{title}: phone", required=True, placeholder="+48 512 345 678"),
            F("Input", f"parent_{i}_email", f"{title}: email", required=True)]


def _sibling(i: int) -> list:
    return [F("Input", f"sibling_{i}_name", f"Sibling {i}: full name", required=True),
            F("Dropdown", f"sibling_{i}_grade", f"Sibling {i}: grade", required=True, options=GRADES)]


SIBLING_GROUPS = [[f"sibling_{i}_name", f"sibling_{i}_grade"] for i in range(1, MAX_SIBLINGS + 1)]
PARENT_2 = [f.name for f in _parent(2, "")]

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_child", "Child",
      C("Accordion", "acc_child", "About the child",
        F("Input", "child_first_name", "First name", required=True),
        F("Input", "child_last_name", "Last name", required=True),
        F("Input", "child_pesel", "PESEL number", required=True, placeholder="11 digits"),
        F("DatePicker", "child_birth_date", "Date of birth", required=True),
        F("Dropdown", "grade", "Grade applying for", required=True, options=GRADES),
        F("Input", "street", "Home address: street and number", required=True),
        F("Input", "postcode", "Postcode", required=True, placeholder="30-001"),
        F("Input", "city", "City", required=True))),
    C("Tab", "tab_parents", "Parents",
      C("Accordion", "acc_parent_1", "Parent or guardian 1",
        *_parent(1, "Parent 1")),
      C("Accordion", "acc_parent_2", "Parent or guardian 2 (optional)",
        F("Checkbox", "has_second_parent", "Add a second parent or guardian"),
        *_parent(2, "Parent 2")),
      C("Accordion", "acc_siblings", "Brothers and sisters at the school",
        F("NumberInput", "sibling_count", "Siblings at Willow Lane Primary (0 to 3)", required=True),
        *[f for i in range(1, MAX_SIBLINGS + 1) for f in _sibling(i)])),
    C("Tab", "tab_care", "Health and day",
      C("Accordion", "acc_medical", "Health",
        F("Checkbox", "has_medical_needs", "My child has allergies, a condition or other medical needs"),
        F("TextArea", "medical_details", "Medical needs and what staff should do", required=True)),
      C("Accordion", "acc_day", "The school day",
        "Lunch costs 12 PLN a day. Clubs run 15:00 to 16:30; a child can join at most 2.",
        F("MultiSelect", "clubs", "After-school clubs (up to 2)",
          options=opts("chess:Chess", "football:Football", "art:Art", "robotics:Robotics", "choir:Choir",
                       "english:English conversation")),
        F("RadioGroup", "lunch_plan", "Lunch", required=True,
          options=opts("none:No school lunch", "standard:Standard lunch", "vegetarian:Vegetarian lunch",
                       "gluten_free:Gluten-free lunch (with a medical note)")),
        F("RadioGroup", "transport", "Getting home", required=True,
          options=opts("parent:Picked up by a parent", "alone:Walks home alone (age 10+)", "bus:School bus")),
        F("Dropdown", "bus_stop", "Bus stop", required=True,
          options=opts("rynek:Rynek Podgorski", "kampus:Kampus", "ruczaj:Ruczaj Park"))),
      C("Accordion", "acc_consent", "Consent",
        F("RadioGroup", "photo_consent", "May the school publish photos of your child?", required=True,
          options=opts("yes:Yes, in school materials and the website", "internal:Only inside the school", "no:No")),
        F("Checkbox", "data_consent", "I agree to the processing of my child's data for enrolment", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Enrolment at Willow Lane Primary School, Krakow",
    "starters": ["Enrol my son in grade 1", "My daughter already has a brother at the school", "What clubs are there?"],
    "persona": "You are Willow Lane Primary School's enrolment assistant. Be kind and clear; English labels, Polish formats.",
    "flow_hints": [
        "The child first: the PESEL (11 digits) must match the date of birth.",
        "Parent 1 is required; a second parent or guardian is optional.",
        "Postcodes look like 30-001; phones are +48 and 9 digits.",
        "A child joins at most 2 after-school clubs.",
        "Only children aged 10 or more may walk home alone.",
    ],
    "glossary": {
        "child_pesel": "The Polish national id number: 11 digits, the first six are the birth date.",
        "postcode": "Polish format NN-NNN, e.g. 30-001.",
        "clubs": "Up to 2 clubs, 15:00 to 16:30.",
        "lunch_plan": "12 PLN a day; gluten-free with a medical note in the health section.",
        "transport": "Walking home alone is allowed from age 10.",
    },
    "pii": ["child_pesel", "child_birth_date", "street", "postcode", "parent_1_phone", "parent_1_email",
            "parent_2_phone", "parent_2_email", "medical_details"],
}

PAGE = {
    "path": "/lab/school-krakow",
    "title": "Willow Lane Primary School, Krakow: enrolment",
    "description": "Willow Lane Primary School's enrolment form for children in grades 1 to 8 in Krakow.",
    "keywords": ["school", "primary school", "enrolment", "enrollment", "krakow", "poland", "child", "pupil"],
    "sections": [
        {"id": "school", "title": "The school",
         "text": "Willow Lane Primary School in Krakow, grades 1 to 8. Lessons in Polish and English. "
                 "The school year starts on 1 September."},
        {"id": "day", "title": "Lunch, clubs and transport",
         "text": "School lunch costs 12 PLN a day (standard, vegetarian, or gluten-free with a medical note). "
                 "After-school clubs run 15:00 to 16:30: chess, football, art, robotics, choir, English conversation; "
                 "a child can join at most 2. The school bus stops at Rynek Podgorski, Kampus and Ruczaj Park. "
                 "Children may walk home alone from age 10."},
    ],
}


def _school_year_start() -> date:
    t = date.today()
    return date(t.year if t.month < 9 else t.year + 1, 9, 1)


def rules(h) -> None:
    p = h.text("child_pesel").replace(" ", "")
    if p:
        if not pesel_ok(p):
            h.error("child_pesel", "A PESEL is 11 digits with a valid check digit: check the number")
        else:
            coded, bd = pesel_birth(p), h.date("child_birth_date")
            if coded and bd and coded != bd:
                h.error("child_birth_date", f"The date of birth does not match the PESEL ({coded.isoformat()})")
    h.a_date("child_birth_date", past=True)
    age = h.age("child_birth_date", _school_year_start())
    if age is not None and not h.has_error("child_birth_date") and not 6 <= age <= 15:
        h.error("child_birth_date", "The child must be 6 to 15 years old on 1 September")
    h.match("postcode", POST_RX, POST_MSG)

    two = h.on("has_second_parent")
    h.show(*PARENT_2, when=two)
    h.require(*PARENT_2, when=two)
    for i in (1, 2):
        h.match(f"parent_{i}_phone", PHONE_RX, PHONE_MSG)
        h.email(f"parent_{i}_email")

    h.number("sibling_count", 0, MAX_SIBLINGS, msg="Enter 0 to 3 siblings", integer=True)
    h.repeat("sibling_count", SIBLING_GROUPS, required=("_name", "_grade"))

    med = h.on("has_medical_needs")
    h.show("medical_details", when=med)
    h.require("medical_details", when=med)
    if len(h.ids("clubs")) > MAX_CLUBS:
        h.error("clubs", "Choose at most 2 clubs")
    if h.id("lunch_plan") == "gluten_free" and not med:
        h.error("lunch_plan", "Gluten-free lunch needs a medical note: tick medical needs and describe it")
    if h.id("transport") == "alone" and age is not None and age < 10:
        h.error("transport", "Only children aged 10 or more may walk home alone")
    bus = h.id("transport") == "bus"
    h.show("bus_stop", when=bus)
    h.require("bus_stop", when=bus)
