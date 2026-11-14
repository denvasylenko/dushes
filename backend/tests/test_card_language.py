"""Question options keep the agent's label in the user's language; the id stays the form's option."""
from __future__ import annotations

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value


def test_translated_labels_with_the_forms_ids(guide, model):
    opts = [{"id": "consumer", "label": "\\u041f\\u043e\\u0442\\u0440\\u0435\\u0431\\u0438\\u0442\\u0435\\u043b\\u044c\\u0441\\u043a\\u0438\\u0439"},   # Russian: consumer
            {"id": "mortgage"}]
    model.script = [say("", ("q1", "ask_user", {"question": "?", "field": "loan_type", "options": opts}))]
    v = interrupt_value(collect(guide, "cl1", message="hi", state=start(guide, LOAN)))
    got = {o["id"]: o["label"] for o in v["options"]}
    assert got["consumer"].startswith("\\u041f") and got["mortgage"] != "mortgage"   # no label given: the form's name


def test_a_fill_card_in_the_users_language(guide, model):
    ru = "\\u0424\\u0430\\u043c\\u0438\\u043b\\u0438\\u044f"   # Russian: surname
    model.script = [say("", ("c1", "propose_changes", {"changes": [
        {"name": "last_name", "value": "Morozova", "label": ru, "shown": "Morozova"}]}))]
    v = interrupt_value(collect(guide, "cl2", message="hi", state=start(guide, LOAN)))
    row = v["changes"][0]
    assert row["label"] == ru and row["value"] == "Morozova" and row["display"] == "Morozova"
