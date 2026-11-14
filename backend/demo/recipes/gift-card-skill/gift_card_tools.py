"""The gift-card skill's tool. Any LangChain tool works: an HTTP call to your API, a database query."""
from __future__ import annotations

from langchain_core.tools import tool

CARDS = {"GC-1234-5678": (50, "2027-03-01"), "GC-0000-1111": (15, "2026-12-31")}   # your card service


@tool
def check_gift_card(code: str) -> str:
    """Look up a gift card balance by its code (format GC-XXXX-XXXX)."""
    c = code.strip().upper()
    if c not in CARDS:
        return f"No gift card {c}. Check the code."
    balance, expiry = CARDS[c]
    return f"Gift card {c}: balance ${balance}, valid until {expiry}."
