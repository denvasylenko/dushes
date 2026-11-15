"""Dushes reports the usage of its own model calls: run_stats with agent "site", before the terminal event."""
from __future__ import annotations

from .conftest import say
from .test_site import form_state, run, site  # noqa: F401 - the fixture


def stats_of(ev):
    return [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == "run_stats"]


def test_a_site_answer_reports_its_model_call(site, model):
    model.script = [say("The branch is open until 6 pm.")]
    ev = run(site, "u1", message="when is the branch open?", state={"page": {"path": "/contacts"}})
    assert [e.get("name", e["type"]) for e in ev][-2:] == ["run_stats", "RUN_FINISHED"]
    s = stats_of(ev)[0]
    assert s["agent"] == "site" and s["thread_id"] == "u1" and [m["kind"] for m in s["models"]] == ["site"]
    assert "model" in s["models"][0] and "tokens" in s
    assert isinstance(s["ttft_ms"], int)   # the run's first word (QA, 2026-11-15: it was empty for every site turn)


def test_the_router_and_every_round_are_counted(site, guide, model):
    model.script = [say("site"), say("", ("n1", "navigate", {"path": "/contacts"})), say("Here are the contacts.")]
    ev = run(site, "u2", message="when is the branch open on Saturday?", state=form_state(guide))
    kinds = [m["kind"] for m in stats_of(ev)[0]["models"]]
    assert kinds[0] == "router" and kinds.count("site") >= 1 and len(stats_of(ev)) == 1


def test_a_turn_of_the_form_agent_keeps_its_own_numbers(site, guide, model):
    model.script = [say("What is your last name?")]
    ev = run(site, "u3", message="my first name is Anna", state=form_state(guide))
    assert all(s.get("agent") != "site" for s in stats_of(ev)) and len(stats_of(ev)) == 1   # Dushes called no model


def test_a_tool_that_does_not_exist_is_a_failed_step_and_a_refused_move_is_not(site, model):
    model.script = [say("", ("x1", "no_such_tool", {})), say("", ("n1", "navigate", {"path": "/contacts"})),
                    say("The branch is open until 6 pm. Want me to open Contacts?")]
    ev = run(site, "u4", message="when is the branch open?", state={"page": {"path": "/"}})
    res = {e["toolCallId"]: e for e in ev if e["type"] == "TOOL_CALL_RESULT"}
    assert res["x1"]["error"] is True and "error" not in res["n1"]
