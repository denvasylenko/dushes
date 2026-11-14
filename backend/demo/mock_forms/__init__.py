"""Mock form backend (stands in for the real Java service). Not part of the agent.

Each demo form provides: a JSX string, a function that rebuilds the config from
state, and optionally a domain pack shipped together with the form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import barber, insurance, loan_rules, loan_spec
from .lab import LAB


@dataclass
class MockForm:
    form_id: str
    jsx: str
    compute: Callable[[dict[str, Any] | None], dict[str, Any]]
    domain: dict[str, Any] | None = None   # None: the agent resolves the pack from its own registry


FORMS: dict[str, MockForm] = {
    "loan_application": MockForm("loan_application", loan_spec.FORM_JSX, loan_rules.compute_config),
    "barber_booking": MockForm("barber_booking", barber.FORM_JSX, barber.compute_config, barber.DOMAIN),
    # the held-out domain of the scenario evals (backend/evals/heldout_*.yaml): no prompt rule is tuned on it
    "car_insurance": MockForm("car_insurance", insurance.FORM_JSX, insurance.compute_config, insurance.DOMAIN),
}

# the Form Lab: the QA library of forms (demo/mock_forms/lab/), served on the Lab site at /lab (demo/lab_site.py)
FORMS.update({fid: MockForm(fid, f.jsx, f.compute_config, f.domain) for fid, f in LAB.items()})
