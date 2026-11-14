"""A number or date picker starts inside its bounds, at the model's value or the field's own."""
from __future__ import annotations

from formguide.agent.tools import ToolError, _question_input, _start_value

import pytest


class _E:
    def __init__(self, value=None):
        self.value, self.filled, self.unreadable = value, value is not None, False


class _Ctx:
    def __init__(self, value=None):
        self.ov = {"year": _E(value)}


def test_the_models_value_is_kept_and_clamped():
    inp = _question_input({"type": "number", "min": 2028, "max": 2030, "value": 1988})
    assert _start_value(_Ctx(), "year", inp)["value"] == 2028          # before min: the nearest bound
    inp = _question_input({"type": "number", "min": 2000, "max": 2030, "value": 2012})
    assert _start_value(_Ctx(), "year", inp)["value"] == 2012


def test_without_a_value_the_field_value_or_nothing():
    inp = _question_input({"type": "number", "min": 1950, "max": 2026})
    assert _start_value(_Ctx(2019), "year", inp)["value"] == 2019
    assert "value" not in _start_value(_Ctx(), "year", inp)              # the client starts empty, not at 1988


def test_dates_too_and_impossible_bounds_are_refused():
    inp = _question_input({"type": "date", "min": "2026-01-01", "max": "2026-12-31", "value": "2020-05-01"})
    assert _start_value(_Ctx(), None, inp)["value"] == "2026-01-01"
    with pytest.raises(ToolError, match="no answer fits"):
        _question_input({"type": "number", "min": 2028, "max": 2026})
