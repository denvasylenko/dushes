"""review_form: progress by section, issues from the form, model warnings and fixes, the resume shapes."""
from __future__ import annotations

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value, tool_result


def review(guide, model, thread, args, state=None):
    model.script = [say("", ("r1", "review_form", args))]
    state = state or start(guide, LOAN)
    ev = collect(guide, thread, message="what is left?", state=state)
    return interrupt_value(ev), state


def test_status_mid_way(guide, model):
    v, _ = review(guide, model, "v1", {"mode": "status"})
    assert v["type"] == "review" and v["mode"] == "status" and v["card_id"]
    assert v["sections"] and all(s["left"] <= s["total"] for s in v["sections"])
    assert any(s["left"] for s in v["sections"]) and v["sections"][0]["reveal"]
    assert not any(i.get("kind") == "missing" for i in v["issues"])   # in status mode the sections show them
    labels = [x["label"] for x in v["sections"]]
    assert "Main income" not in labels and len(labels) == len(set(labels))   # only the outermost tabs
    assert guide.thread("v1")["pending_card"]["kind"] == "review"


def test_submit_with_warnings_and_fixes(guide, model):
    v, _ = review(guide, model, "v2", {
        "mode": "submit",
        "warnings": [{"field": "dependents_count", "message": "Many dependants for this income.",
                      "source": "Borrower requirements > Income"}, {"field": "nope", "message": "x"}],
        "fixes": {"phone_mobile": "+79001234567", "dependents_count": "lots"}})
    errors = [i for i in v["issues"] if i["severity"] == "error"]
    warns = [i for i in v["issues"] if i["severity"] == "warning"]
    assert errors and v["issues"].index(errors[-1]) < v["issues"].index(warns[0])   # errors first
    assert [w["field"] for w in warns] == ["dependents_count"]
    assert warns[0]["source"] == {"title": "Borrower requirements > Income"} and "fix" not in warns[0]
    phone = next(i for i in errors if i["field"] == "phone_mobile")
    assert phone["fix"]["value"] == "+79001234567" and phone["reveal"]


def test_resume_shapes(guide, model):
    v, state = review(guide, model, "v3", {"mode": "submit"})
    cfg = {**state["config"], "state": {**state["config"]["state"], "phone_mobile": "+79001234567"}}
    model.script = [say("Fixed.")]
    collect(guide, "v3", resume={"action": "fixed", "names": ["phone_mobile"], "config": cfg})
    out = tool_result(model, "r1")
    assert "applied the fixes for: phone_mobile" in out and "Do not propose" in out
    entry = next(e for e in guide.thread("v3")["transcript"] if e["kind"] == "review")
    assert entry["status"] == "answered" and entry["action"] == "fixed"

    review(guide, model, "v4", {"mode": "submit"})
    model.script = [say("Ok.")]
    collect(guide, "v4", resume={"action": "submit"})
    assert "confirm_action" in tool_result(model, "r1")
    review(guide, model, "v5", {"mode": "status"})
    model.script = [say("Ok.")]
    collect(guide, "v5", resume={"accepted": False})
    assert tool_result(model, "r1") == "The user closed the review."


def test_a_real_error_is_never_crowded_out(guide, model):
    # the live case: many empty required fields on the first tabs, one real error on the Loan tab
    state = start(guide, LOAN)
    state["config"]["props"]["loan_amount"]["error"] = "At least 20% of the loan amount"
    for mode in ("status", "submit"):
        v, _ = review(guide, model, f"v6{mode}", {"mode": mode}, state=state)
        first = v["issues"][0]
        assert first["field"] == "loan_amount" and first["message"].startswith("At least 20%") and "kind" not in first
        assert first["reveal"]
    gaps = [i for i in v["issues"] if i.get("kind") == "missing"]          # submit: one row per section
    assert gaps and all(i["message"].endswith("still empty") for i in gaps)
    assert len({i["label"] for i in gaps}) == len(gaps)
    assert next(i for i in gaps if i["label"] == "Applicant")["message"].split()[0].isdigit()
