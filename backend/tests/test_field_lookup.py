"""A field named by its outline number or its label still resolves; a miss names the closest field."""
from __future__ import annotations

from demo.mock_forms import FORMS

from .conftest import say
from .test_agent import collect, start
from .test_questions import interrupt_value

NEWS = FORMS["newsletter_signup"]


def _card(guide, model, name, thread):
    model.script = [say("", ("c1", "propose_changes", {"changes": [{"name": name, "value": "maya@example.com"}]})),
                    say("Done.")]
    return interrupt_value(collect(guide, thread, message="sign me up: maya@example.com", state=start(guide, NEWS)))


def test_the_outline_number_and_the_label_find_the_field(guide, model):
    for i, name in enumerate(["email", "1.2", "Email address", "Join the newsletter / Email address"]):
        v = _card(guide, model, name, f"fl{i}")
        assert v and [c["name"] for c in v["changes"]] == ["email"], name


def test_a_miss_names_the_closest_field(guide, model):
    assert _card(guide, model, "emial", "fl9") is None
    tool = " ".join(str(m.content) for call in model.calls for m in call if getattr(m, "type", "") == "tool")
    assert "Did you mean email?" in tool
