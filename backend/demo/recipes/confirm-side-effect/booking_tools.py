"""A tool with a side effect: it sends the booking to the salon's system."""
from __future__ import annotations

import uuid

from langchain_core.tools import tool

SENT: list[str] = []   # what reached the salon (your booking API)


@tool
def send_booking_request(summary: str) -> str:
    """Send the booking to the salon once the form is complete. summary: the service, barber, date and time."""
    ref = f"BK-{uuid.uuid4().hex[:6].upper()}"
    SENT.append(f"{ref}: {summary}")
    return f"Booking {ref} sent to the salon."
