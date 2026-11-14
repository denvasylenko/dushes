"""Lab form: a bike repair shop's feedback survey (tiny: an NPS score 0-10, a comment, an optional contact email).

Rules: the score is required; the comment is required only when the score is 6 or less; ticking "may we contact
you" reveals and requires the email field.
"""
from __future__ import annotations

from ..dsl import C, F

FORM_ID = "feedback_nps"

FORM = C(
    "Accordion", "main", "How did we do?",
    F("RadioGroup", "score", "How likely are you to recommend us to a friend? (0 = not at all, 10 = extremely)",
      required=True, options=[{"id": str(i), "name": str(i)} for i in range(11)]),
    F("TextArea", "comment", "What could we do better?"),
    F("Checkbox", "may_contact", "You may contact me about my feedback"),
    F("Input", "contact_email", "Email for our reply", required=True),
)

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Feedback",
    "starters": ["I want to leave feedback", "Give you a 9", "My repair took too long"],
    "persona": "You are Spoke & Chain Cycle Repair's feedback assistant. Thank people; never argue with a score.",
    "flow_hints": [
        "Ask for the 0-10 score first.",
        "A score of 6 or less needs a comment on what to improve.",
        "The email is asked only if the customer agrees to be contacted.",
    ],
    "glossary": {"score": "0 means not at all likely to recommend, 10 means extremely likely."},
    "pii": ["contact_email"],
}

PAGE = {
    "path": "/lab/bike-repair-feedback",
    "title": "Spoke & Chain Cycle Repair: feedback",
    "description": "Spoke & Chain Cycle Repair, a neighbourhood bike workshop: tell us how your repair went.",
    "keywords": ["bike", "bicycle", "repair", "feedback", "survey", "review"],
    "sections": [{"id": "feedback", "title": "Your feedback",
                  "text": "We read every answer. If you give us 6 or less, please tell us what went wrong. "
                          "We only contact you if you tick the box and leave an email."}],
}


def rules(h) -> None:
    raw = h.id("score")
    try:
        s = int(raw) if raw is not None else None
    except ValueError:
        s = None
    h.require("comment", when=s is not None and s <= 6)
    h.show("contact_email", when=h.on("may_contact"))
    h.require("contact_email", when=h.on("may_contact"))
    h.email("contact_email")
