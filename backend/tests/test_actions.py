"""Agent actions: the config, the auto rules and the client's capabilities."""
import pytest

from formguide.agent import actions as act
from formguide.agent.prompts import system_prompt
from formguide.config import load_config
from formguide.domain.packs import DomainPack

from .conftest import say
from .test_agent import BARBER, collect, start


def names(model):
    return {t["function"]["name"] if isinstance(t, dict) else t.name for t in model.bound}


def test_parse_config_defaults_and_errors():
    cfg = act.parse_config({"request_file": False})
    assert cfg["request_file"] is False and cfg["ask_user"] is True and cfg["ask_documents"] == "auto"
    with pytest.raises(ValueError, match="unknown"):
        act.parse_config({"upload": False})
    with pytest.raises(ValueError, match="true, false or auto"):
        act.parse_config({"ask_user": "yes"})


def test_resolve_auto_and_capabilities():
    cfg = act.parse_config(None)
    on = act.resolve(cfg, has_documents=False, attachments=True, caps=None)
    assert "ask_documents" not in on and {"request_file", "extract_from_attachment", "review_form"} <= on
    on = act.resolve(cfg, has_documents=True, attachments=False, caps=None)
    assert "ask_documents" in on and "request_file" not in on and "extract_from_attachment" not in on
    on = act.resolve(cfg, has_documents=True, attachments=True, caps=frozenset({"ask", "confirm"}))
    assert {"ask_user", "confirm_action", "ask_documents", "focus_field"} <= on
    assert not {"request_file", "review_form"} & on                  # the client cannot show them
    on = act.resolve(cfg, has_documents=False, attachments=True, caps=frozenset({"ask.details", "upload.camera"}))
    assert {"ask_user", "request_file"} <= on and "confirm_action" not in on   # a variant implies its card
    assert act.capabilities("nope") is None and act.capabilities(["ask", 3]) == {"ask", "3"}


def test_switched_off_action_is_not_bound_and_not_in_the_prompt(guide, model):
    guide.config.actions = {"request_file": False, "confirm_action": False}
    model.script = [say("", ("x", "request_file", {"prompt": "passport"})), say("ok")]
    collect(guide, "a1", message="hello", state=start(guide, BARBER))
    bound = names(model)
    assert "request_file" not in bound and "confirm_action" not in bound and "ask_user" in bound
    prompt = model.calls[0][0].content
    assert "request_file" not in prompt and "confirm_action" not in prompt and "ask_user" in prompt
    tool_msgs = [m for m in model.calls[1] if getattr(m, "tool_call_id", None) == "x"]
    assert tool_msgs and "not available" in tool_msgs[0].content


def test_client_capabilities_limit_the_run(guide, model):
    model.script = [say("hi")]
    collect(guide, "a2", message="hello", state=start(guide, BARBER), capabilities=["ask", "confirm", "focus"])
    bound = names(model)
    assert {"ask_user", "confirm_action", "focus_field"} <= bound
    assert "request_file" not in bound and "review_form" not in bound
    model.script = [say("hi")]
    collect(guide, "a3", message="hello", state=start(guide, BARBER))          # an old client: all on
    assert {"request_file", "review_form"} <= names(model)


def test_prompt_rules_follow_actions():
    pack = DomainPack(form_id="f", title="F", kb_documents=["tariffs.md"])
    full = system_prompt(pack)
    assert "review_form" in full and "ask_documents" in full
    less = system_prompt(pack, actions=frozenset({"ask_user"}))
    assert "review_form" not in less and "ask_documents" not in less and "ask_user" in less


def test_yaml_actions_and_attachments(tmp_path):
    p = tmp_path / "formguide.yaml"
    p.write_text("model: anthropic:claude-haiku-5-5\nactions: {review_form: false}\n"
                 "attachments: {enabled: false, privacy_note: Stays on our server.}\n")
    cfg = load_config(p)
    assert cfg.actions["review_form"] is False and cfg.attachments_enabled is False
    assert cfg.privacy_note == "Stays on our server."
    p.write_text("model: anthropic:claude-haiku-5-5\nattachments: {size: 3}\n")
    with pytest.raises(ValueError, match="attachments"):
        load_config(p)
