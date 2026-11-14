"""Scenario evals (scripts/evals.py): the scenario files, the checks that cap the score, the regression limit,
and an offline pass over every scenario with scripted models."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evals  # noqa: E402


def test_every_scenario_file_loads():
    names = [s.name for s in evals.load_all()]
    assert len(names) >= 8 and len(set(names)) == len(names)


def test_an_unknown_key_is_named(tmp_path):
    (tmp_path / "typo.yaml").write_text("name: typo\npersona: p\ngoal: g\nexpct: {says: [x]}\n")
    with pytest.raises(evals.ScenarioError, match=r"typo\.yaml: unknown key expct"):
        evals.load_all(folder=tmp_path)
    (tmp_path / "typo.yaml").write_text("name: typo\npersona: p\ngoal: g\nexpect: {sayz: [x]}\n")
    with pytest.raises(evals.ScenarioError, match=r"unknown key expect\.sayz"):
        evals.load_all(folder=tmp_path)


def test_failed_checks_cap_the_score():
    assert evals.capped(9, [{"ok": True, "cap": 3}]) == 9
    assert evals.capped(9, [{"ok": False, "cap": 5}]) == 5
    assert evals.capped(9, [{"ok": False, "cap": 5}, {"ok": False, "cap": 3}]) == 3   # an invented fact caps at 3


def test_a_regression_fails_the_run():
    base = {"average": 8.6, "scenarios": {"a": 9, "b": 8.2}}
    results = [{"name": "a", "score": 8.0, "min_score": 6}, {"name": "b", "score": 7.8, "min_score": 6}]
    text, failed, avg = evals.summarize(results, base, margin=0.5)
    assert failed and avg == 7.9
    assert "(was 9)" in text and "below the baseline 8.6" in text
    _, failed, _ = evals.summarize(results, {"scenarios": {"a": 8.2, "b": 8.2}}, margin=0.5)
    assert not failed                                                     # within the margin
    _, failed, _ = evals.summarize(results[:1], base, margin=0.5)
    assert failed                                                         # a subset is compared with its own baseline (9)
    _, failed, _ = evals.summarize([{"name": "a", "score": 5, "min_score": 6}], None, margin=0.5)
    assert failed                                                         # below its own min_score


def test_final_form_values():
    assert evals._same({"id": "auto", "name": "Car loan"}, "auto") and evals._same({"id": "auto", "name": "Car loan"}, "car loan")
    assert evals._same("1985-07-14", "1985-07-14") and not evals._same(None, "x") and evals._same(True, True)
    assert not evals._same("true", True)
    assert evals._same(None, None) and evals._same("", None) and not evals._same("Barsik", None)   # null: left empty


def test_a_partial_run_keeps_the_other_baseline_scores(tmp_path, monkeypatch):
    base = tmp_path / "baseline.json"
    base.write_text('{"average": 8, "scenarios": {"other": 8}}')
    monkeypatch.setattr(evals, "play", lambda sc, *a, **k: {"name": sc.name, "file": sc.file, "score": 9.0, "judge_score": 9.0,
                                                             "min_score": 1, "checks": [], "lost": [], "path": "/", "transcript": None})
    monkeypatch.setattr(evals, "models_for", lambda spec: (None, None))
    monkeypatch.setattr(evals, "User", lambda m, sc: None)
    evals.run(["opening_hours"], save_baseline=True, baseline_file=base)
    import json
    assert json.loads(base.read_text())["scenarios"] == {"other": 8, "opening_hours": 9.0}


def test_every_scenario_runs_offline(tmp_path):
    report, _ = evals.run(offline=True, baseline_file=tmp_path / "none.json")
    by = {r["name"]: r for r in report["scenarios"]}
    assert set(by) == {s.name for s in evals.load_all()}
    for r in by.values():                                                 # each one ran through the demo's HTTP API
        assert not any(c["check"] == "the scenario ran" for c in r["checks"]), r
        assert not any(c["check"] == "no run errors" for c in r["checks"]), r
    agent_check = {r["name"]: c for r in by.values() for c in r["checks"] if c["check"].startswith("answered by")}
    assert agent_check["opening_hours"]["ok"]                             # Dushes answered on the home page
    assert agent_check["loan_form_fill"]["ok"]                            # the form agent on the form page


def test_repeated_runs_give_the_mean_and_the_worst():
    r = evals.combine([{"name": "a", "score": 8.0, "min_score": 6, "checks": []},
                       {"name": "a", "score": 4.0, "min_score": 6, "checks": [{"check": "x", "ok": False}]}])
    assert r["score"] == 6.0 and r["worst"] == 4.0 and r["best"] == 8.0 and len(r["runs"]) == 2
    assert r["checks"] == [{"check": "x", "ok": False}]                   # the worst run's checks are shown
    text, _, _ = evals.summarize([r], None, 0.5)
    assert "worst 4.0, best 8.0" in text


def test_a_red_team_user_is_told_to_break_the_rules():
    sc = evals.Scenario(name="x", persona="p", goal="g", red_team=True)
    assert "red-team" in evals._user_brief(sc) and "red-team" not in evals._user_brief(evals.Scenario(name="x", persona="p", goal="g"))


def test_a_forbidden_phrase_is_matched_as_whole_words():
    assert evals._says("The penalty is 5% a day.", "penalty is")
    assert not evals._says("The penalty isn't listed anywhere.", "penalty is")
    assert not evals._says("The penalty is\u2019nt listed.", "penalty is") and evals._says("I have ticked them.", "i have ticked")
