"""Tools contributed by demo skills. Any LangChain tool works: an HTTP call to your API, a DB query, ..."""
from __future__ import annotations

from langchain_core.tools import tool

_CARDS = {"GC-1234-5678": (50, "2027-03-01"), "GC-0000-1111": (15, "2026-12-31")}


@tool
def check_gift_card(code: str) -> str:
    """Look up a gift card balance by its code (format GC-XXXX-XXXX)."""
    c = code.strip().upper()
    if c not in _CARDS:
        return f"No gift card {c}. Check the code."
    balance, expiry = _CARDS[c]
    return f"Gift card {c}: balance ${balance}, valid until {expiry}."


@tool
def check_promo_code(code: str) -> str:
    """Check a promo code for a car insurance quote and return its discount."""
    # For the QA scenarios only (DEMO_FAILING_TOOL=1 on a test stand, never on the public demo): the tool fails
    # for every code, the way a partner's service does when it is down, so a scenario can check what the
    # assistant says after a tool error: one more try at most, then plain words, never "the code is applied".
    raise RuntimeError("the promo service did not answer")
