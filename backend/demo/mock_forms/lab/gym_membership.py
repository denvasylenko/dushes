"""Lab form: a gym membership in Hamburg (medium; German formats, SEPA direct debit, age rules, a promo code).

Rules: members are 16 or older (error under 16); under 18 reveals a guardian's name and signature checkbox; the
student plan reveals a student card upload and needs a member under 26; the start date is today or within 60 days;
the IBAN is checked; the promo code, when given, must be WELCOME10 (any case) or it is an error.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..dsl import C, F, opts

FORM_ID = "gym_membership"
PROMO = "WELCOME10"

FORM = C(
    "Tabs", "main", None,
    C("Tab", "tab_member", "1. Member",
      C("Accordion", "acc_member", "About you",
        F("Input", "first_name", "First name", required=True),
        F("Input", "last_name", "Last name", required=True),
        F("DatePicker", "birth_date", "Date of birth", required=True),
        F("Input", "email", "Email", required=True),
        F("Input", "phone", "Mobile phone", placeholder="+49 151 23456789"),
        F("Input", "street", "Street and number", required=True),
        F("Input", "postcode", "Postcode", required=True, placeholder="20095"),
        F("Input", "city", "City", required=True)),
      C("Accordion", "acc_guardian", "Parent or guardian",
        "Members aged 16 or 17 need a parent or guardian's consent.",
        F("Input", "guardian_name", "Guardian's full name", required=True),
        F("Checkbox", "guardian_signature", "I am the parent or guardian and I sign this membership", required=True))),
    C("Tab", "tab_plan", "2. Membership",
      C("Accordion", "acc_plan", "Plan",
        F("RadioGroup", "plan", "Plan", required=True,
          options=opts("monthly:Monthly (39 EUR a month, cancel with 1 month's notice)",
                       "annual:Annual (399 EUR a year, paid once)",
                       "student:Student (24 EUR a month, under 26 with a valid student card)")),
        F("FileUpload", "student_card", "Student card (photo or PDF)", required=True),
        F("DatePicker", "start_date", "Start date", required=True),
        F("Checkbox", "freeze_option", "Add the freeze option (5 EUR a month: pause up to 3 months a year)"),
        F("Input", "promo_code", "Promo code"))),
    C("Tab", "tab_payment", "3. Payment",
      C("Accordion", "acc_sepa", "SEPA direct debit",
        "The joining fee of 29 EUR is collected with the first payment.",
        F("Input", "account_holder", "Account holder", required=True),
        F("Input", "iban", "IBAN", required=True, placeholder="DE89 3704 0044 0532 0130 00"),
        F("Checkbox", "sepa_mandate", "I authorise Hafenkraft Fitness to collect payments by SEPA direct debit",
          required=True))),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Gym membership",
    "starters": ["Sign me up for the student plan", "My son is 17, can he join?", "I have a promo code"],
    "persona": "You are Hafenkraft Fitness Hamburg's membership assistant. Be upbeat and brief.",
    "flow_hints": [
        "Members must be at least 16; members aged 16 or 17 need a guardian's name and signature.",
        "The student plan needs a student card upload and a member under 26.",
        "Only one promo code is valid: WELCOME10 (10 EUR off the joining fee). Do not invent other codes.",
        "Payment is by SEPA direct debit: the account holder, an IBAN and the mandate.",
    ],
    "glossary": {
        "plan": "Monthly 39 EUR a month (1 month's notice), Annual 399 EUR a year, Student 24 EUR a month (under 26).",
        "freeze_option": "5 EUR a month; lets you pause the membership for up to 3 months a year.",
        "promo_code": "WELCOME10 takes 10 EUR off the 29 EUR joining fee.",
        "start_date": "Today or within the next 60 days.",
    },
    "pii": ["email", "phone", "street", "postcode", "iban", "account_holder", "birth_date"],
}

PAGE = {
    "path": "/lab/gym",
    "title": "Hafenkraft Fitness Hamburg: join",
    "description": "Hafenkraft Fitness Hamburg's membership sign-up form.",
    "keywords": ["gym", "fitness", "membership", "workout", "student", "hamburg"],
    "sections": [
        {"id": "prices", "title": "Plans and prices",
         "text": "Monthly 39 EUR a month, cancel with 1 month's notice. Annual 399 EUR a year. Student 24 EUR a month for "
                 "members under 26 with a valid student card. Joining fee 29 EUR. Freeze option 5 EUR a month "
                 "(pause up to 3 months a year)."},
        {"id": "rules", "title": "Who can join",
         "text": "Members must be 16 or older; members aged 16 or 17 need a parent or guardian's signature. "
                 "Current offer: promo code WELCOME10 takes 10 EUR off the joining fee."},
        {"id": "hours", "title": "Opening hours", "text": "Open every day 6:00 to 23:00."},
    ],
}


def rules(h) -> None:
    age = h.age("birth_date")
    h.a_date("birth_date", past=True)
    if age is not None and age < 16 and not h.has_error("birth_date"):
        h.error("birth_date", "Members must be at least 16 years old")
    minor = age is not None and 16 <= age < 18
    h.show("acc_guardian", "guardian_name", "guardian_signature", when=minor)
    h.require("guardian_name", "guardian_signature", when=minor)
    h.email("email")
    h.phone("phone")
    h.match("postcode", r"\d{5}", "A German postcode has 5 digits")

    student = h.id("plan") == "student"
    h.show("student_card", when=student)
    h.require("student_card", when=student)
    if student and age is not None and age >= 26:
        h.error("plan", "The student plan is for members under 26: choose Monthly or Annual")

    s = h.date("start_date")
    h.a_date("start_date", future=True, msg="The start date cannot be in the past")
    if s and s > date.today() + timedelta(days=60) and not h.has_error("start_date"):
        h.error("start_date", "Choose a start date within the next 60 days")

    code = h.text("promo_code")
    if code and code.upper() != PROMO:
        h.error("promo_code", "This promo code is not valid; leave it empty if you have none")

    h.iban("iban")
