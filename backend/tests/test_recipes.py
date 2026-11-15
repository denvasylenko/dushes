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
    late = recipes.site_numbers({**rep, "at": "2026-11-14T23:55:37", "ended": "2026-11-15T00:00:03"}, path, target)
    assert late["skill-scoped"]["date"] == "2026-11-15"   # a run over midnight carries the day it ended, as its report's name does


def test_bench_writes_the_docs_speed_numbers(tmp_path):
    import argparse

    import bench
    target = tmp_path / "speed.json"
    target.write_text(json.dumps({"model": "x", "scenarios": [{"name": "fill", "label": "fill (long)", "short": "fill"}]}))
    run = lambda ttft, turn: {"ttft_ms": ttft, "turn_ms": turn, "tools": 2, "tokens": {"input": 1000, "output": 100},
                              "cache_hit_rate": 0.9, "models_used": [{"model": "claude-haiku-5-5"}], "tool_names": ["propose_changes"]}
    rows = [{"scenario": "fill", "ttft_median_ms": 800, "turn_median_ms": 5200, "runs": [run(800, 5200), run(900, 5000)]}]
    a = argparse.Namespace(commit="abc1234", base="https://dushes-ai.fly.dev", repeat=2, model=None,
                           prices=str(recipes.HERE.parent / "site" / "src" / "data" / "prices.json"))
    d = bench.site_speed(rows, a, ["--repeat", "2", "--site"], target)
    assert d["model"] == "Claude Haiku 5.5" and d["commit"] == "abc1234" and d["repeat"] == 2
    assert d["scenarios"][0] == {"name": "fill", "label": "fill (long)", "short": "fill", "ttft_s": 0.8, "turn_s": 5.2,
                                 "tools": 2, "tokens_in": 1000, "tokens_out": 100, "cache": 0.9}
    assert bench.git_commit("https://dushes-ai.fly.dev") == ""
    docs = [{"scenario": "documents", "ttft_median_ms": 900, "turn_median_ms": 4000, "runs": [run(900, 4000)]}]
    assert bench.site_speed(docs, a, [], target)["scenarios"] == []   # a documents turn without ask_documents is left out
    assert d["prices"]["model_id"] == "claude-haiku-5-5" and d["prices"]["checked"] and d["prices"]["source"].startswith("https://")


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
    prices = {"checked": "2026-11-14", "source": "https://example.test/pricing",
              "models": {"claude-haiku-5-5": {"input": 0.1, "output": 0.5, "cache_read": 0.01},
                         "claude-sonnet-5-5": {"input": 3, "output": 15, "cache_read": 0.3}}}
    assert model_bench.row(rep, prices, {})["cost_per_turn"] is not None
    assert model_bench.wilson(9, 10) == [0.596, 0.982] and model_bench.wilson(0, 0) is None
    rj = tmp_path / "rejudge.json"
    rj.write_text(json.dumps({"second_judge": "openai:other", "n": 2, "report": "missing.json", "mean_first": 7.0, "mean_second": 6.5,
                              "rows": [{"name": "a", "first": 9, "second": 8.5, "diff": -0.5}, {"name": "b", "first": 5, "second": 3, "diff": -2}]}))
    m = model_bench.site_models([rep], prices, "Apple M1 Pro, 16 GB", [], [rj], tmp_path / "models.json")
    one = m["models"][0]
    assert one["id"] == "anthropic:claude-haiku-5-5" and not one["local"] and one["runs"] == 2 and one["passes"] == 1
    assert one["pass_rate"] == 0.5 and one["interval95"] == model_bench.wilson(1, 2) and one["code_check_failures"] == 1
    assert one["sets"]["heldout"]["pass_rate"] == 1.0 and one["sets"]["form"]["scenarios"] == 2
    assert one["ttft_p50_s"] == 0.9 and one["turn_p95_s"] == 4.0 and one["cost_per_turn_usd"] == 0.00011
    assert one["quality_per_dollar"] == round(0.5 / 0.00011)
    assert one["losses"][0]["scenario"] == "lab_b_fill" and one["losses"][0]["failed_checks"] == ["x"]
    assert m["second_judge"] == {"model": "openai:other", "sample": 2, "agreement": 0.5, "means": {"missing.json": {"first": 7.0, "second": 6.5}}}
    assert m["method"]["judge_model"] == "claude-sonnet-5-5" and m["method"]["prices_checked"] == "2026-11-14" and m["total_cost_usd"] is not None
    with pytest.raises(SystemExit, match="not comparable"):
        model_bench.site_models([rep, {**rep, "commit": "def"}], prices, "", [], None, tmp_path / "models.json")


def test_bench_prices_a_turn_from_the_price_file():
    import bench
    prices = json.loads((recipes.HERE.parent / "site" / "src" / "data" / "prices.json").read_text())
    hk = prices["models"]["claude-haiku-5-5"]
    small = {"model": "claude-haiku-5-5", "input_tokens": 20000, "cache_read_tokens": 15000, "cache_write_tokens": 4000, "output_tokens": 500}
    want = (1000 * hk["input"] + 15000 * hk["cache_read"] + 4000 * hk["cache_write"] + 500 * hk["output"]) / 1e6
    assert abs(bench.call_cost(small, hk) - want) < 1e-12
    big = {**small, "input_tokens": 150000}                       # over 100K: the long-prompt prices
    o = {**hk, **hk["over"]}
    assert abs(bench.call_cost(big, hk) - (131000 * o["input"] + 15000 * o["cache_read"] + 4000 * o["cache_write"] + 500 * o["output"]) / 1e6) < 1e-12
    run = {"ttft_ms": 900, "total_ms": 4000, "model_ms": 3000, "tool_ms": 500, "tools": [], "models": [small],
           "tokens": {"input": 20000, "output": 500, "cache_read": 15000}}
    assert bench.summarize([run], prices)["cost_usd"] == round(want, 5)
    assert bench.summarize([run], {"input": 0.1, "output": 0.5, "cache_read": 0.01})["cost_usd"] > 0   # the flat file still works
    assert "unpriced_models" in bench.summarize([{**run, "models": [{**small, "model": "gpt-x"}]}], prices)


def test_recipe_tool_modules_have_unique_names():
    """Every recipe folder is on sys.path while it runs, so two tool modules with one name would clash."""
    names = [p.name for p in recipes.RECIPES.glob("*/*.py")]
    assert len(names) == len(set(names)), names


def test_site_bench_verdicts_and_sets():
    import site_bench as sb
    assert sb.verdict("no navigation", {"path": "/faq"}) == "needless" and sb.verdict("no navigation", None) == "quiet"
    assert sb.verdict({"path": "/loans", "tab": "mortgage"}, {"path": "/loans", "tab": "mortgage"}) == "right"
    assert sb.verdict({"path": "/loans", "tab": "mortgage"}, {"path": "/loans"}) == "page only"
    assert sb.verdict({"path": "/faq"}, {"path": "/contacts"}) == "wrong" and sb.verdict({"path": "/faq"}, None) == "missed"
    from formguide.site import SiteMap
    site = SiteMap.load(recipes.HERE / "demo" / "site.yaml")
    data = json.loads((sb.SETS / "nav_demo.json").read_text())
    for p in data["phrases"]:   # every expected page and part is on the demo site
        if p["expect"] != "no navigation":
            page = site.page(p["expect"]["path"])
            assert page, p
            part = p["expect"].get("tab") or p["expect"].get("accordion") or p["expect"].get("section")
            assert not part or page.part(part), p


def test_bench_prices_a_call_without_a_model_id_by_the_turns_model():
    import bench
    prices = json.loads((recipes.HERE.parent / "site" / "src" / "data" / "prices.json").read_text())
    call = {"input_tokens": 1000, "cache_read_tokens": 0, "cache_write_tokens": 0, "output_tokens": 10}
    run = {"ttft_ms": 1, "total_ms": 1, "model_ms": 1, "tool_ms": 0, "tools": [], "tokens": {"input": 2000, "output": 20, "cache_read": 0},
           "models": [{**call, "model": "claude-haiku-5-5"}, {**call, "model": None}]}
    out = bench.summarize([run], prices)
    assert "unpriced_models" not in out and out["cost_usd"] > 0


def test_a_recipe_can_forbid_words_in_the_replies():
    sc = recipes.load(recipes.SCENARIOS / "recipe_chat_only_form_yes.yaml")
    bad = recipes.verdict(sc, [], {}, [], ["\n\U0001f464 hi", "\U0001f916 Look at the form on the right."])
    assert [c["check"] for c in bad if c["check"].startswith("never says") and not c["ok"]] == ["never says look at the form", "never says on the right"]
    assert all(c["ok"] for c in recipes.verdict(sc, [], {}, [], ["\U0001f916 Who is the new deputy?"]) if c["check"].startswith("never says"))
    assert not recipes._ran(["The user declined; the tool was not run."]) and recipes._ran(["Deputy change DP-1 sent."])
    two = recipes.verdict(sc, [], {}, ["confirm", "set_fields", "confirm"], [])
    assert [c["ok"] for c in two if c["check"] == "at most 1 confirm card"] == [False]
    assert [c["ok"] for c in recipes.verdict(sc, [], {}, ["confirm"], []) if c["check"] == "at most 1 confirm card"] == [True]
    held = lambda c: [x["ok"] for x in recipes.verdict(sc, [], {}, [], [], c) if x["check"].startswith("every confirm card")]
    assert held(["submit_deputy_change"]) == [True] and held([None, "submit_deputy_change"]) == [False] and held([]) == [False]


def test_the_scripted_user_gives_a_date_picker_a_date():
    from datetime import date
    sunday = date(2026, 11, 15)
    assert recipes.typed("next Tuesday", {"type": "date"}, sunday) == "2026-11-17"
    assert recipes.typed("next Sunday", {"type": "date"}, sunday) == "2026-11-22"      # never today
    assert recipes.typed("next Tuesday", {"type": "text"}, sunday) == "next Tuesday"
    assert recipes.typed("2027-03-01", {"type": "date"}, sunday) == "2027-03-01" and recipes.typed("", {"type": "date"}) == ""


def test_the_scripted_user_s_answer_fills_the_field_the_question_is_about():
    class Lab:
        def compute(self, state):
            return {"state": dict(state or {}), "props": {}}

    chat = recipes.FormChat.__new__(recipes.FormChat)
    chat.form, chat.config, chat.ui, chat.answer = Lab(), {"state": {"consent": False}}, {}, ""
    chat.cards, chat.log, sent = [], [], []
    chat._resume = lambda reply, depth: sent.append(reply)
    card = {"type": "ask", "question": "Do you agree?", "field": "consent", "applies": True,
            "options": [{"id": "yes", "label": "Yes", "value": True}, {"id": "no", "label": "No", "value": False}]}
    chat._answer(card, 0)
    assert chat.config["state"]["consent"] is True and sent[0]["config"] == chat.config and sent[0]["answer"] == {"ids": ["yes"]}
    chat._answer({**card, "applies": False, "field": None}, 0)
    assert "config" not in sent[1]
