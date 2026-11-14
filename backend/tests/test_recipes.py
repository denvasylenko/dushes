"""Recipe evals (scripts/recipes.py): every scenario loads, every recipe folder builds its own app, and an
offline run reaches the agent; the checks and the docs numbers (site/src/data/recipes.json) are computed right."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import recipes  # noqa: E402

ALL = recipes.load_all()


def test_every_recipe_scenario_loads():
    assert ALL and len({s.name for s in ALL}) == len(ALL)


@pytest.mark.parametrize("sc", [s for s in ALL if not s.transcribe], ids=lambda s: s.name)
def test_a_recipe_runs_offline(sc, tmp_path):
    out = recipes.run([sc.name], runs=1, offline=True, write_site=False)
    r = out["scenarios"][0]["results"][0]
    assert not any(c["check"] == "the run ran" for c in r["checks"]), r


def test_the_checks():
    sc = recipes.RecipeScenario(name="x", recipe="r", expect={"tools": ["a", "b"], "order": True, "never_tools": ["z"],
                                                              "tool_args": {"use_skill": {"name": "gift_cards"}},
                                                              "executed": {"send": False}})
    calls = [("a", {}), ("use_skill", {"name": "Gift_Cards"}), ("b", {}), ("send", {})]
    ok = {c["check"]: c["ok"] for c in recipes.verdict(sc, calls, {"send": ["Not executed: waiting for a yes"]})}
    assert all(ok.values()), ok
    bad = {c["check"]: c["ok"] for c in recipes.verdict(sc, [("b", {}), ("a", {}), ("z", {})], {"send": ["Sent."]})}
    assert not bad["in order a > b"] and not bad["never calls z"] and not bad["send never ran"]


def test_site_numbers_add_up_a_recipes_scenarios(tmp_path):
    rep = {"at": "2026-11-14T12:00:00", "scenarios": [
        {"recipe": "skill-scoped", "tool": "use_skill", "runs": 10, "hits": 9, "model": "claude-haiku-5-5"},
        {"recipe": "skill-scoped", "tool": "not use_skill", "runs": 10, "hits": 10, "model": "claude-haiku-5-5"}]}
    target = tmp_path / "recipes.json"
    target.write_text('{"other": {"runs": 1}}')
    path = recipes.HERE / "scripts" / "runs" / "recipes-x.json"
    data = recipes.site_numbers(rep, path, target)
    assert data["skill-scoped"] == {"runs": 20, "hits": 19, "scenarios": 2, "tool": "use_skill; not use_skill", "model": "claude-haiku-5-5",
                                    "date": "2026-11-14", "report": "backend/scripts/runs/recipes-x.json"}
    assert json.loads(target.read_text())["other"] == {"runs": 1}


def test_bench_writes_the_docs_speed_numbers(tmp_path):
    import argparse

    import bench
    target = tmp_path / "speed.json"
    target.write_text(json.dumps({"model": "x", "scenarios": [{"name": "fill", "label": "fill (long)", "short": "fill"}]}))
    run = lambda ttft, turn: {"ttft_ms": ttft, "turn_ms": turn, "tools": 2, "tokens": {"input": 1000, "output": 100},
                              "cache_hit_rate": 0.9, "models_used": [{"model": "claude-haiku-5-5"}]}
    rows = [{"scenario": "fill", "ttft_median_ms": 800, "turn_median_ms": 5200, "runs": [run(800, 5200), run(900, 5000)]}]
    a = argparse.Namespace(commit="abc1234", base="https://dushes-ai.fly.dev", repeat=2)
    d = bench.site_speed(rows, a, ["--repeat", "2", "--site"], target)
    assert d["model"] == "Claude Haiku 5.5" and d["commit"] == "abc1234" and d["repeat"] == 2
    assert d["scenarios"][0] == {"name": "fill", "label": "fill (long)", "short": "fill", "ttft_s": 0.8, "turn_s": 5.2,
                                 "tools": 2, "tokens_in": 1000, "tokens_out": 100, "cache": 0.9}
    assert bench.git_commit("https://dushes-ai.fly.dev") == ""


def test_the_docs_get_the_evals_and_models_numbers(tmp_path):
    import eval_summary
    import model_bench
    sc = lambda n, score, tags: {"name": n, "score": score, "min_score": 6, "tags": tags, "checks": [{"check": "x", "ok": score > 6, "cap": 5}],
                                 "lost": [{"points": 2, "reason": "It invented a price. Then it repeated itself."}],
                                 "tokens": {"assistant": {"input": 1000, "output": 100, "cache_read": 500}},
                                 "runs_stats": [{"ttft_ms": 900, "total_ms": 4000, "tools": 2, "tool_errors": 0, "output_tokens": 100, "model_ms": 2000}]}
    rep = {"at": "2026-11-15T01:00:00", "started": "2026-11-14T23:00:00", "average": 7.0, "commit": "abc", "repeat": 3,
           "agent_model": "anthropic:claude-haiku-5-5", "user_model": "claude-sonnet-5-5", "judge_model": "claude-sonnet-5-5",
           "scenarios": [sc("heldout_a", 9, ["heldout"]), sc("lab_b_fill", 5, ["lab", "fill"])]}
    d = eval_summary.site_evals(rep, eval_summary.RUNS / "evals-x.json", eval_summary.HAIKU, tmp_path / "evals.json")
    assert d["date_from"] == "2026-11-14" and d["date_to"] == "2026-11-15" and d["heldout"] == {"average": 9.0, "min": 9, "count": 1}
    assert d["worst"][0] == {"name": "lab_b_fill", "score": 5, "reason": "It invented a price."} and d["target"]["met"]
    row = model_bench.row(rep, {"anthropic:claude-haiku-5-5": {"input": 0.1, "output": 0.5, "cache_read": 0.01}}, {})
    m = model_bench.site_models([row], "Apple M1 Pro, 16 GB", [], tmp_path / "models.json")
    assert m["models"][0]["model"] == "Claude Haiku 5.5" and m["models"][0]["bar"] and m["cheapest_passing"] == "anthropic:claude-haiku-5-5"
    with pytest.raises(SystemExit, match="not comparable"):
        model_bench.site_models([row, {**row, "commit": "def"}], "", [], tmp_path / "models.json")
