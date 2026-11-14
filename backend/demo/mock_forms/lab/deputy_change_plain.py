"""Lab form: the same "change my deputy" form as deputy_change, but its pack says nothing about the form being
hidden: the page tells the agent with state.ui.form_visible = false (the hidden-form scenarios).
"""
from __future__ import annotations

from .deputy_change import FORM, rules  # noqa: F401  (the same fields and rules)

FORM_ID = "deputy_change_plain"

DOMAIN = {
    "form_id": FORM_ID,
    "title": "Change my deputy",
    "starters": ["Can I change my deputy?"],
    "persona": "You are the Alder & Finch staff portal's assistant. Short and practical.",
    "flow_hints": ["All four values are needed: the deputy's name, their work email, the start date and the reason."],
    "glossary": {"reason": "Vacation and leave are temporary; a permanent change replaces the deputy until changed again."},
    "pii": ["deputy_email"],
}

PAGE = {
    "path": "/lab/alder-finch-portal",
    "title": "Alder & Finch staff portal",
    "description": "Alder & Finch's staff portal: the assistant changes who stands in for you while you are away.",
    "keywords": ["deputy", "stand-in", "substitute", "absence", "staff", "portal"],
    "sections": [{"id": "deputy", "title": "Your deputy",
                  "text": "A deputy approves requests for you while you are away. The assistant takes the person's "
                          "name, their work email, the start date and the reason."}],
}
