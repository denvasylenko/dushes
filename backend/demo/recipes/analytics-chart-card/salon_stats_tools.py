"""The analytics skill's tool: numbers from your own data (a database, an analytics API)."""
from __future__ import annotations

import json

from langchain_core.tools import tool

VISITS = {"Mon": 31, "Tue": 24, "Wed": 28, "Thu": 35, "Fri": 52, "Sat": 61}   # last 4 weeks; closed on Sunday


@tool
def get_visits_by_day() -> str:
    """Visits by day of the week over the last 4 weeks, as JSON {day: visits}."""
    return json.dumps(VISITS)
