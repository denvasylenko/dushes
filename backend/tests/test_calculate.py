"""calculate: exact, safe arithmetic; the prompt's rule on explaining a form's figure."""
from __future__ import annotations

import pytest

from formguide.agent.prompts import CORE
from formguide.agent.tools import ToolError, _t_calculate


def test_an_annuity_payment_is_exact():
    out = _t_calculate({"expression": "500000 * (0.219/12) / (1 - (1 + 0.219/12) ** -36)"}, None)
    assert out.endswith("= 19069.2") or "= 19069" in out


def test_only_arithmetic_is_allowed():
    for bad in ("__import__('os')", "a + 1", "2 ** 100000", "1/0", ""):
        with pytest.raises(ToolError):
            _t_calculate({"expression": bad}, None)


def test_the_prompt_says_how_to_explain_a_figure():
    core = " ".join(CORE.split())
    assert "say first that the form does not state its method" in core
    assert "so the form's method differs" in core and "with calculate" in core
    assert "when a field note or the page facts state the method, give it as the form's own words" in core


def test_a_locked_value_is_the_forms_value():
    core = " ".join(CORE.split())
    assert "is the form's real, current value" in core and "never call it a placeholder" in core
