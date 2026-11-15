"""Named model choices: a run names one, a conversation keeps it, the client is told which model answers."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from formguide import FormGuide, GuideConfig, Models
from formguide.config import load_config
from formguide.domain.packs import DomainPackRegistry
from formguide.guide import ModelChoiceError
from formguide.knowledge.base import KnowledgeBase
from formguide.server import create_router
from formguide.site import Dushes, SiteMap

from .conftest import DEMO, ScriptedChatModel, say
from .test_agent import collect, start
from .test_questions import LOAN
from .test_site import SITE, form_state, run


@pytest.fixture
def luna() -> ScriptedChatModel:
    return ScriptedChatModel()


@pytest.fixture
def two(tmp_path, model, luna) -> FormGuide:
    return FormGuide(GuideConfig(
        models=Models(agent=model), data_dir=tmp_path,
        model_choices={"haiku": {"label": "Haiku"}, "luna": {"label": "Luna (experimental)", "agent": luna}},
        domain_packs=DomainPackRegistry(directory=DEMO / "domain_packs"),
        knowledge=KnowledgeBase(tmp_path / "kb"), translate_missing=False))


def custom(ev, name):
    return [e["value"] for e in ev if e.get("type") == "CUSTOM" and e.get("name") == name]


def test_a_run_answers_on_the_choice_it_names(two, model, luna):
    luna.script = [say("Luna here.")]
    ev = collect(two, "m1", message="hi", state=start(two, LOAN), model="luna")
    assert len(luna.calls) == 1 and not model.calls
    assert custom(ev, "model") == [{"choice": "luna", "label": "Luna (experimental)", "model": custom(ev, "model")[0]["model"]}]
    names = [e.get("name") or e["type"] for e in ev]
    assert names.index("model") == names.index("RUN_STARTED") + 1          # before the first word

    model.script = [say("Haiku here.")]
    ev = collect(two, "m2", message="hi", state=start(two, LOAN))           # no name: the first choice
    assert len(model.calls) == 1 and custom(ev, "model")[0]["choice"] == "haiku"


def test_a_conversation_keeps_its_model(two, model, luna):
    luna.script = [say("One."), say("Two.")]
    collect(two, "m3", message="hi", state=start(two, LOAN), model="luna")
    collect(two, "m3", message="again", state=start(two, LOAN))             # no name: the thread's choice
    assert len(luna.calls) == 2 and not model.calls and two.thread_choice("m3") == "luna"
    with pytest.raises(ModelChoiceError) as e:
        collect(two, "m3", message="now haiku", state=start(two, LOAN), model="haiku")
    assert e.value.status == 409 and e.value.detail["code"] == "model_fixed" and e.value.detail["choice"] == "luna"
    assert [x["kind"] for x in two.thread("m3")["transcript"]].count("model") == 1


def test_names_outside_the_configuration_are_refused(two, guide):
    with pytest.raises(ModelChoiceError) as e:
        two.check_model("m4", "gpt-9")
    assert e.value.status == 422 and e.value.detail["choices"] == ["haiku", "luna"]
    with pytest.raises(ModelChoiceError):                                   # a server without choices takes no name
        guide.check_model("m4", "luna")
    assert guide.check_model("m4", None) is None and guide.model_choices() == []


def test_the_helpers_and_the_researcher_follow_the_choice(two, model, luna):
    sets = two._choices
    assert sets["haiku"].models.agent is model and sets["haiku"].models.research is model
    for role in ("agent", "research", "extract", "memory"):
        assert getattr(sets["luna"].models, role) is luna, role
    assert sets["luna"].translation is luna
    assert [(c["name"], c["default"], c["usable"]) for c in two.model_choices()] == [("haiku", True, True), ("luna", False, True)]


def test_the_router_lists_the_choices_and_refuses_before_the_stream(two, luna):
    app = FastAPI()
    app.include_router(create_router(two))
    c = TestClient(app)
    assert [x["name"] for x in c.get("/models").json()["choices"]] == ["haiku", "luna"]
    st = start(two, LOAN)
    body = {"threadId": "m5", "runId": "r1", "state": st, "messages": [{"id": "u1", "role": "user", "content": "hi"}],
            "tools": [], "context": [], "forwardedProps": {"model": "luna"}}
    luna.script = [say("Hello.")]
    assert c.post("/run", json=body).status_code == 200 and len(luna.calls) == 1
    r = c.post("/run", json={**body, "runId": "r2", "forwardedProps": {"model": "haiku"}})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "model_fixed"
    r = c.post("/run", json={**body, "threadId": "m6", "forwardedProps": {"model": "opus"}})
    assert r.status_code == 422 and "haiku, luna" in r.json()["detail"]["detail"]


def test_dushes_and_its_form_threads_run_on_the_site_threads_choice(two, model, luna):
    site = Dushes(two, SiteMap.load(SITE))
    luna.script = [say("The branch is open until 6 pm.")]
    ev = run(site, "s1", message="when is the branch open?", state={"page": {"path": "/contacts"}}, model="luna")
    assert len(luna.calls) == 1 and not model.calls
    assert [m["choice"] for m in custom(ev, "model")] == ["luna"]
    luna.script = [say("form"), say("What is your last name?")]                    # the router, then the form agent
    ev = run(site, "s1", message="my first name is Anna", state=form_state(two))   # no name given: the thread's
    assert len(luna.calls) == 3 and not model.calls and len(custom(ev, "model")) == 1
    assert two.thread_choice("s1-loan_application") == "luna"
    with pytest.raises(ModelChoiceError):
        run(site, "s1", message="hi", state={"page": {"path": "/contacts"}}, model="haiku")


def test_choices_in_a_configuration_file(tmp_path):
    p = tmp_path / "formguide.yaml"
    p.write_text('model: "anthropic:claude-haiku-5-5"\nmodels:\n  choices:\n    haiku: {label: Haiku}\n'
                 '    luna: {label: "Luna (experimental)", agent: "anthropic:claude-haiku-5-5"}\n')
    cfg = load_config(p)
    assert list(cfg.model_choices) == ["haiku", "luna"] and cfg.model_choices["luna"]["label"] == "Luna (experimental)"
    p.write_text('model: "anthropic:claude-haiku-5-5"\nmodels:\n  choices:\n    luna: {agnet: x}\n')
    with pytest.raises(ValueError) as e:
        load_config(p)
    assert "models.choices.luna: unknown key(s) ['agnet']" in str(e.value)
