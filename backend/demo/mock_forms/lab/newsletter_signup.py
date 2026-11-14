"""Lab form: a coffee roaster's newsletter sign-up (tiny: one field and nothing else, no tabs).

Rules: the email is required and must look like an email address.
"""
from __future__ import annotations

from ..dsl import C, F

FORM_ID = "newsletter_signup"

FORM = C(
    "Accordion", "main", "Join the newsletter",
    "One email a month: new single-origin lots, brewing tips and early access to limited roasts. Unsubscribe any time.",
    F("Input", "email", "Email address", required=True, placeholder="you@example.com"),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Newsletter sign-up",
    "starters": ["Sign me up for the newsletter", "How often do you send emails?"],
    "persona": "You are Kettle Hill Roasters' friendly assistant. Keep it short: the form has a single field.",
    "flow_hints": ["The only field is the email address; once it is valid the form is done."],
    "glossary": {"email": "The newsletter goes out once a month; every email has an unsubscribe link."},
    "pii": ["email"],
}

PAGE = {
    "path": "/lab/coffee-newsletter",
    "title": "Kettle Hill Roasters: newsletter",
    "description": "Kettle Hill Roasters, a small-batch coffee roaster: sign up for the monthly newsletter.",
    "keywords": ["coffee", "roaster", "beans", "newsletter", "subscribe", "email"],
    "sections": [{"id": "newsletter", "title": "Our newsletter",
                  "text": "We send one email a month with new single-origin lots, brewing tips and early access to "
                          "limited roasts. No spam, and every email has an unsubscribe link."}],
}


def rules(h) -> None:
    h.email("email")
