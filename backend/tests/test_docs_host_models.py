"""The public host's model choices: prices by model, a budget per choice and in total, the fallback."""
from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from docs_ai import host
from formguide.models import ModelSet, ResolvedModels

from .conftest import ScriptedChatModel, say

TABLE = {"claude-haiku-5-5": {"input": 0.1, "output": 0.5, "cache_read": 0.01, "cache_write": 0.125,
                              "over": {"tokens": 100000, "input": 0.5, "output": 2.5, "cache_read": 0.05}},
         "gpt-6-luna": {"input": 0.2, "output": 1.0, "cache_read": 0.02}}


def _fresh(monkeypatch, **limits):
    for k, v in {"TABLE": TABLE, "PRICES": None, "COST_DAY": 5.0, "COST_CHOICES": {"haiku": 3.0, "luna": 2.0}, **limits}.items():
        monkeypatch.setattr(host, k, v)
    host._threads.clear()
    host._day = host.Day("")


def _two(monkeypatch, tmp_path):
    """Both choices usable, a transcript store of the test's own, and the agent's run replaced by a stub that
    records the choice it was asked for (no graph, no database: the host's rules are what is tested here)."""
    from formguide.transcript import FileTranscriptStore, new_entry
    m = ScriptedChatModel()
    sets = {}
    for name, label in (("haiku", "Haiku"), ("luna", "Luna (experimental)")):
        sets[name] = ModelSet(name, label, ResolvedModels(agent=m, research=m, compile=m, extract=m, memory=m), None, m)
    monkeypatch.setattr(host.guide, "_choices", sets)
    monkeypatch.setattr(host.guide, "transcripts", FileTranscriptStore(tmp_path))
    asked: list[str | None] = []

    async def run_detached(**kw):
        choice = host.guide.check_model(kw["thread_id"], kw.get("model"))
        if host.guide.thread_choice(kw["thread_id"]) is None:
            host.guide.transcripts.append(kw["thread_id"], new_entry("model", choice=choice))
        asked.append(choice)
        yield {"type": "RUN_STARTED", "threadId": kw["thread_id"], "runId": kw["run_id"]}
        yield {"type": "CUSTOM", "name": "model", "value": {"choice": choice, "label": sets[choice].label, "model": "x"}}
        yield {"type": "RUN_FINISHED", "threadId": kw["thread_id"], "runId": kw["run_id"]}

    monkeypatch.setattr(host.guide, "run_detached", run_detached)
    return asked


def _body(thread, model=None):
    state = {"jsx_hash": host.LANDING["landing_loan"], "form_id": "landing_loan", "config": {"props": {}, "state": {}}}
    return {"threadId": thread, "runId": "r", "state": state, "messages": [{"id": "m", "role": "user", "content": "hi"}],
            "tools": [], "context": [], "forwardedProps": {"model": model} if model else {}}


def _events(r):
    return [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]


def test_each_call_is_priced_by_its_own_model(monkeypatch):
    _fresh(monkeypatch)
    cost, tokens = host.run_cost({"models": [
        {"model": "claude-haiku-5-5", "input_tokens": 1_000_000, "output_tokens": 0},        # over the tier: 0.50
        {"model": "anthropic:claude-haiku-5-5", "input_tokens": 10_000, "output_tokens": 10_000},   # 0.001 + 0.005
        {"model": "gpt-6-luna", "input_tokens": 100_000, "output_tokens": 100_000, "cache_read_tokens": 50_000},
        {"model": "a-model-nobody-priced", "input_tokens": 1_000_000, "output_tokens": 1_000_000}]})
    assert round(cost, 4) == round(0.5 + 0.006 + (0.01 + 0.1 + 0.001), 4)        # the unknown one costs nothing here
    assert tokens["input"] == 2_110_000
    monkeypatch.setattr(host, "PRICES", host.prices("1,2,0.1"))                  # a row for models the table lacks
    assert host.run_cost({"models": [{"model": "a-model-nobody-priced", "input_tokens": 1_000_000}]})[0] == 1.0


def test_a_budget_per_choice_and_in_total(monkeypatch):
    _fresh(monkeypatch)
    log = logging.getLogger("formguide.stats")
    log.info(json.dumps({"choice": "luna", "models": [{"model": "gpt-6-luna", "output_tokens": 2_100_000}]}))   # $2.10
    assert round(host.today().by_choice["luna"], 2) == 2.1 and not host.left("luna") and host.left("haiku")
    assert host.demo_limit("b1", "1.1.1.1", choice="luna") == "model_cost"
    assert host.demo_limit("b1", "1.1.1.1", choice="haiku") is None
    log.info(json.dumps({"choice": "haiku", "models": [{"model": "claude-haiku-5-5", "output_tokens": 5_900_000}]}))  # $2.95
    assert host.today().cost >= 5 and host.demo_limit("b2", "1.1.1.1", choice="haiku") == "cost" and not host.left("haiku")
    assert host.today().numbers()["cost_by_choice"] == {"luna": 2.1, "haiku": 2.95}


def test_the_choices_are_listed_with_what_is_left(monkeypatch):
    _fresh(monkeypatch)
    with TestClient(host.app) as c:
        got = {x["name"]: x for x in c.get("/agent/models").json()["choices"]}
    assert got["haiku"]["default"] and got["haiku"]["left"] and got["luna"]["label"] == "Luna (experimental)"
    assert got["luna"]["usable"] is False                              # no OPENAI_API_KEY here: the page hides it


def test_a_new_conversation_falls_back_with_a_line(monkeypatch, tmp_path):
    _fresh(monkeypatch)
    asked = _two(monkeypatch, tmp_path)
    host.today().by_choice["luna"] = 2.0                               # Luna's budget is gone, the total is not
    with TestClient(host.app) as c:
        r = c.post("/agent/run", json=_body("f1", "luna"))
        assert r.status_code == 200 and asked == ["haiku"]             # the run went on with the other choice
        ev = _events(r)
        notice = next(e["value"] for e in ev if e.get("name") == "notice")
        assert notice == {"text": "Luna (experimental)'s demo budget for today is used up; Haiku answers.",
                          "code": "model_fallback", "choice": "haiku"}
        assert ev[0]["type"] == "RUN_STARTED" and ev[1].get("name") == "notice"
        assert host.guide.thread_choice("f1") == "haiku"
        assert c.post("/agent/run", json=_body("f0", "haiku")).status_code == 200 and asked == ["haiku", "haiku"]
        assert not any(e.get("name") == "notice" for e in _events(c.post("/agent/run", json=_body("f0"))))


def test_an_existing_conversation_is_told_to_start_a_new_one(monkeypatch, tmp_path):
    _fresh(monkeypatch)
    asked = _two(monkeypatch, tmp_path)
    with TestClient(host.app) as c:
        assert c.post("/agent/run", json=_body("f2", "luna")).status_code == 200 and asked == ["luna"]
        host.today().by_choice["luna"] = 2.0
        r = c.post("/agent/run", json=_body("f2"))
        assert r.status_code == 429 and r.json()["reason"] == "model_cost"
        assert r.json()["choice"] == "luna" and r.json()["other"] == "haiku"
        host.today().by_choice["haiku"] = 3.0                          # neither has budget left
        assert c.post("/agent/run", json=_body("f3", "luna")).json()["reason"] == "cost"
        assert asked == ["luna"]                                       # no refused run reached the agent


def test_a_code_holder_has_the_wider_limits_and_the_sites_totals_still_hold(monkeypatch):
    """The owner (2026-11-17), after the public demo refused him with 429 in his own test: a person who entered an
    activation code gets the limits of his dev host (100 a conversation, 400 a day); a visitor without a code keeps
    the public ones; the site's totals (runs, dollars a day) are the same for both."""
    _fresh(monkeypatch)
    monkeypatch.setattr(host, "_holders", {})
    monkeypatch.setattr(host, "_threads", host.defaultdict(int))
    assert not host.code_holder("9.9.9.9") and host.code_holder("9.9.9.9", mark=True) and host.code_holder("9.9.9.9")
    assert not host.code_holder("8.8.8.8")
    for _ in range(host.PER_THREAD):
        assert host.demo_limit("t-guest", "8.8.8.8") is None
    assert host.demo_limit("t-guest", "8.8.8.8") == "thread"                     # a visitor: 15 a conversation
    for _ in range(host.PER_THREAD + 5):
        assert host.demo_limit("t-ours", "9.9.9.9", holder=True) is None         # a code holder goes on
    assert host.CODE_PER_THREAD == 100 and host.CODE_PER_DAY == 400
    monkeypatch.setattr(host, "RUNS_DAY", host.today().runs)                     # the site's total is spent
    assert host.demo_limit("t-ours-2", "9.9.9.9", holder=True) == "runs"
