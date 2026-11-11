"""Mock form backend (stands in for the real Java service). Not part of the agent.

Each demo form provides: a JSX string, a function that rebuilds the config from
state, and optionally a domain pack shipped together with the form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import barber, loan_rules, loan_spec


@dataclass
class MockForm:
    form_id: str
    jsx: str
    compute: Callable[[dict[str, Any] | None], dict[str, Any]]
    domain: dict[str, Any] | None = None   # None: the agent resolves the pack from its own registry


FORMS: dict[str, MockForm] = {
    "loan_application": MockForm("loan_application", loan_spec.FORM_JSX, loan_rules.compute_config),
    "barber_booking": MockForm("barber_booking", barber.FORM_JSX, barber.compute_config, barber.DOMAIN),
}
