"""The demo's always-failing tool, for the QA scenario of a tool error (rule F43 of the factory-settings map)."""
from __future__ import annotations

import pytest

from demo.skill_tools import check_promo_code


def test_the_promo_tool_fails_for_every_code():
    assert check_promo_code.name == "check_promo_code"
    for code in ("WELCOME10", "", "GC-1234-5678"):
        with pytest.raises(RuntimeError):
            check_promo_code.invoke({"code": code})


def test_it_is_on_only_where_a_stand_asks_for_it():
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "demo" / "app.py").read_text()
    assert 'os.environ.get("DEMO_FAILING_TOOL") == "1"' in source and "check_promo_code" in source
