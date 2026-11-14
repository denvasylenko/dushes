"""A held tool's result reaches the client; both prompts allow checking the user's own arithmetic."""
from __future__ import annotations

from langchain_core.tools import tool

from formguide.agent.prompts import CORE
from formguide.site import agent as site_agent

from .test_agent import collect
from .test_interactions import pause
from .conftest import say


def test_a_confirmed_held_tool_sends_its_result(guide, model):
    @tool
    def submit_application(reference: str) -> str:
        """Submit the application to the bank."""
        return f"submitted {reference}"

    guide._tools.append(submit_application)
    guide.config.confirm_tools = ["submit_application"]
    pause(guide, model, "hr1", "submit_application", {"reference": "A-1"})
    model.script = [say("Done.")]
    ev = collect(guide, "hr1", resume={"accepted": True})
    got = [e for e in ev if e["type"] == "TOOL_CALL_RESULT" and e["toolCallId"] == "t1"]
    assert got and got[0]["content"] == "The user confirmed. submitted A-1"


def test_checking_the_users_arithmetic_is_allowed():
    core = " ".join(CORE.split())
    assert "When the user does the arithmetic on those figures, you may check it" in core
    assert "Do not send the user to sources the business never names" in core
    assert "never pick one silently" in core
    site = " ".join(site_agent.SYSTEM.split())
    assert "checking the user's own arithmetic on figures the site gave is fine" in site
