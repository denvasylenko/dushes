"""Every run_stats model entry names its model, suggestions included."""
from __future__ import annotations

from formguide.stats import model_id


def test_model_id_reads_the_usual_attributes():
    class A:
        model = "claude-haiku-5-5"

    class B:
        model_name = "gpt-5"

    assert model_id(A()) == "claude-haiku-5-5" and model_id(B()) == "gpt-5" and model_id(object()) is None


def test_suggestions_report_their_model(guide, model):
    from .conftest import say
    from .test_agent import collect, start
    from .test_questions import LOAN
    object.__setattr__(model, "model_name", "scripted-1")   # a real chat model names itself
    guide.suggestions_model = model
    model.script = [say("Here is the first step."), say('[{"text": "What is next?"}]')]
    ev = collect(guide, "sm1", message="where do I start?", state=start(guide, LOAN))
    stats = next(e["value"] for e in ev if e.get("name") == "run_stats")
    sug = [m for m in stats["models"] if m["kind"] == "suggestions"]
    assert sug and all(m["model"] for m in stats["models"]), stats["models"]
