"""The host's own tool: it sends the "change my deputy" form to the staff portal's API."""
from __future__ import annotations

import uuid

from langchain_core.tools import tool

SENT: list[str] = []   # what reached the portal (your own API)


@tool
def submit_deputy_change(summary: str) -> str:
    """Send the deputy change once all four values are set. summary: the deputy's name and email, the start date
    and the reason."""
    ref = f"DP-{uuid.uuid4().hex[:6].upper()}"
    SENT.append(f"{ref}: {summary}")
    return f"Deputy change {ref} sent."
