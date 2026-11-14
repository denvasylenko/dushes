"""The tools of the two gift-card skills."""
from __future__ import annotations

from langchain_core.tools import tool

CARDS = {"GC-1234-5678": (50, "2027-03-01"), "GC-0000-1111": (15, "2026-12-31")}


@tool
def check_gift_card(code: str) -> str:
    """Look up a gift card balance by its code (format GC-XXXX-XXXX)."""
    c = code.strip().upper()
    if c not in CARDS:
        return f"No gift card {c}. Check the code."
    balance, expiry = CARDS[c]
    return f"Gift card {c}: balance ${balance}, valid until {expiry}."


@tool
def refund_gift_card(code: str) -> str:
    """Refund the unused balance of a gift card to the payment card it was bought with."""
    c = code.strip().upper()
    if c not in CARDS:
        return f"No gift card {c}. Check the code."
    return f"Refund of ${CARDS[c][0]} for {c} started: it reaches the original payment card in 5 working days."
