"""Lab form: registering a birth at the Norland Civil Registry (medium, computed options).

Rules: a birth is registered within 42 days: the date of birth is today or in the last 42 days, never in the future;
a birth outside a hospital needs the place's address; the father's section is shown unless "father not declared" is
ticked; "the parents are married" is asked only with a declared father and reveals the marriage certificate number
(MC- and 8 digits), required; the child's surname options are computed from the parents' surnames: the mother's,
the father's (when declared), and both hyphenated (mother-father, when declared); a surname choice that is no longer
offered is dropped; national id numbers have 11 digits; a declarant who is not a parent gives their name; the
hospital's birth notice upload is required.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "birth_registration"
SEQUENTIAL = False
DEADLINE_DAYS = 42

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_child", "1. Child",
      C("Accordion", "acc_child", "The child",
        "Register a birth within 42 days.",
        F("Input", "child_first_names", "First name(s)", required=True),
        F("Dropdown", "child_surname", "Surname", required=True,
          options=opts("mother:Mother's surname", "father:Father's surname", "both:Both surnames, hyphenated")),
        F("DatePicker", "child_birth_date", "Date of birth", required=True),
        F("Input", "child_birth_time", "Time of birth (HH:MM)"),
        F("RadioGroup", "child_sex", "Sex", required=True, options=opts("f:Female", "m:Male", "x:Undetermined")),
        F("Dropdown", "birth_place_type", "Place of birth", required=True,
          options=opts("hospital:Hospital or maternity unit", "home:At home", "other:Elsewhere")),
        F("Input", "birth_place_name", "Hospital name or address of the place", required=True),
        F("Input", "birth_city", "Town or city", required=True))),
    C("Tab", "tab_parents", "2. Parents",
      C("Accordion", "acc_mother", "Mother",
        F("Input", "mother_surname", "Mother's surname", required=True),
        F("Input", "mother_first_names", "Mother's first name(s)", required=True),
        F("DatePicker", "mother_birth_date", "Mother's date of birth", required=True),
        F("Input", "mother_id_number", "Mother's national id number (11 digits)", required=True),
        F("Input", "mother_address", "Mother's address", required=True)),
      C("Accordion", "acc_father", "Father",
        F("Checkbox", "father_not_declared", "The father is not declared"),
        F("Input", "father_surname", "Father's surname", required=True),
        F("Input", "father_first_names", "Father's first name(s)", required=True),
        F("DatePicker", "father_birth_date", "Father's date of birth", required=True),
        F("Input", "father_id_number", "Father's national id number (11 digits)", required=True),
        F("Checkbox", "parents_married", "The parents are married to each other"),
        F("Input", "marriage_cert_number", "Marriage certificate number", required=True, placeholder="MC-12345678"))),
    C("Tab", "tab_declarant", "3. Declarant",
      C("Accordion", "acc_declarant", "Who registers the birth",
        F("RadioGroup", "declarant_role", "I am", required=True,
          options=opts("mother:The mother", "father:The father", "other:Someone else present at the birth")),
        F("Input", "declarant_name", "Your full name", required=True),
        F("Input", "declarant_phone", "Your phone", required=True),
        F("FileUpload", "birth_notice", "Medical birth notice from the hospital or midwife", required=True),
        F("Checkbox", "declaration", "I declare that this information is true", required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Birth registration",
    "starters": ["Register my newborn son", "Our baby was born at home", "Can she have both our surnames?"],
    "persona": "You are the Norland Civil Registry's assistant for birth registration. Be warm and exact.",
    "flow_hints": [
        "Ask the parents' surnames before the child's surname: the choices come from them.",
        "The father's section is skipped when the father is not declared.",
        "A birth must be registered within 42 days.",
    ],
    "glossary": {
        "child_birth_date": "Today or within the last 42 days.",
        "child_surname": "The mother's surname, the father's, or both hyphenated (mother's first).",
        "marriage_cert_number": "MC- followed by 8 digits, e.g. MC-12345678.",
        "mother_id_number": "11 digits.",
        "father_id_number": "11 digits.",
    },
    "pii": ["mother_id_number", "father_id_number", "mother_address", "declarant_phone", "mother_birth_date",
            "father_birth_date"],
}

PAGE = {
    "path": "/lab/norland-birth",
    "title": "Norland Civil Registry: register a birth",
    "description": "Register a child's birth with the Norland Civil Registry.",
    "keywords": ["birth", "registration", "newborn", "baby", "civil registry", "birth certificate"],
    "sections": [
        {"id": "rules", "title": "What you need",
         "text": "Register a birth within 42 days. Bring the medical birth notice from the hospital or midwife. "
                 "The child can take the mother's surname, the father's, or both hyphenated with the mother's first. "
                 "Married parents give their marriage certificate number. Registration is free; the first birth "
                 "certificate is free and copies cost 8 EUR."},
    ],
}


def _id11(h, n: str) -> None:
    h.match(n, r"\d{11}", "A national id number has 11 digits")


def rules(h) -> None:
    today = date.today()
    h.a_date("child_birth_date", past=True, msg="The date of birth cannot be in the future")
    h.a_date("child_birth_date", after=today - timedelta(days=DEADLINE_DAYS),
             msg="More than 42 days have passed: register the birth in person at the registry")
    h.match("child_birth_time", r"([01]\d|2[0-3]):[0-5]\d", "Write the time as HH:MM, e.g. 07:45")
    hosp = h.id("birth_place_type") == "hospital"
    h.pr["birth_place_name"]["label"] = "Hospital name" if hosp else "Address of the place of birth"

    h.a_date("mother_birth_date", past=True)
    h.a_date("father_birth_date", past=True)
    _id11(h, "mother_id_number")
    _id11(h, "father_id_number")
    father = not h.on("father_not_declared")
    fn = ["father_surname", "father_first_names", "father_birth_date", "father_id_number"]
    h.show(*fn, "parents_married", when=father)
    h.require(*fn, when=father)
    married = father and h.on("parents_married")
    h.show("marriage_cert_number", when=married)
    h.require("marriage_cert_number", when=married)
    h.match("marriage_cert_number", r"(?i)MC-\d{8}", "A marriage certificate number looks like MC-12345678")

    # the child's surname choices come from the parents' surnames
    ms, fs = h.text("mother_surname"), h.text("father_surname")
    o = [{"id": "mother", "name": ms or "Mother's surname"}]
    if father:
        o.append({"id": "father", "name": fs or "Father's surname"})
        if not (ms and fs and ms.lower() == fs.lower()):
            o.append({"id": "both", "name": f"{ms}-{fs}" if ms and fs else "Both surnames, hyphenated"})
    h.options("child_surname", o)
    cur = h.val("child_surname")
    if isinstance(cur, dict):
        hit = next((x for x in o if x["id"] == cur.get("id")), None)
        if hit:
            h.set("child_surname", dict(hit))

    other = h.id("declarant_role") == "other"
    h.show("declarant_name", when=other)
    h.require("declarant_name", when=other)
    h.phone("declarant_phone")
