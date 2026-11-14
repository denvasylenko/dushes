"""The Form Lab (demo/mock_forms/lab/): every form compiles, its JSX parses, its rules run on empty and on
filled state, and every lab scenario (evals/*.yaml on the Lab site) names a lab form, a page and real fields."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from demo.mock_forms import FORMS
from demo.mock_forms.lab import LAB, site_map
from formguide.form.layout import LayoutIndex
from formguide.site import SiteMap

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evals  # noqa: E402

LAB_SCENARIOS = [s for s in evals.load_all() if s.site == "/lab"]


def test_the_lab_has_forms_and_a_site():
    assert len(LAB) >= 1 and all(fid in FORMS for fid in LAB)
    site = SiteMap.load(site_map())
    assert {p.form for p in site.pages if p.form} == set(LAB)


@pytest.mark.parametrize("fid", sorted(LAB))
def test_a_lab_form_compiles(fid):
    f = LAB[fid]
    lay = LayoutIndex(f.jsx)
    assert not [w for w in lay.warnings if "unknown tag" in w or "unbalanced" in w or "unclosed" in w], lay.warnings
    cfg = f.compute_config(None)
    assert set(cfg["state"]) <= set(cfg["props"])
    if f.domain is not None:
        assert f.domain.get("form_id") == fid
        for n in f.domain.get("pii") or []:
            assert n in cfg["props"], f"pii field {n} is not on the form"
    assert f.page["path"].startswith("/lab/")
    # the rules survive odd values in every field
    junk = {n: v for n in cfg["state"] for v in ["???"]}
    f.compute_config(junk)
    f.compute_config({n: {"id": "x", "name": "x"} for n in cfg["state"]})


@pytest.mark.parametrize("sc", LAB_SCENARIOS, ids=lambda s: s.name)
def test_a_lab_scenario_names_real_things(sc):
    pages = {p["path"]: p for p in site_map()["pages"]}
    assert sc.page in pages, f"{sc.file}: no lab page {sc.page}"
    form = sc.form or pages[sc.page].get("form")
    if sc.form:
        assert sc.form in LAB and pages[sc.page].get("form") in (None, sc.form), f"{sc.file}: form {sc.form} is not on {sc.page}"
    names = set(LAB[form].compute_config(None)["props"]) if form else set()
    for n in [*sc.fields, *sc.values]:
        assert n in names or any(n in LAB[f].compute_config(None)["props"] for f in LAB), f"{sc.file}: no field {n}"


def test_numbers_match_by_value():
    assert evals._same(1.0, "1") and evals._same("2,5", 2.5) and not evals._same("2", "3") and evals._same("abc", "ABC")


def test_a_reply_to_a_quote_is_sent_like_the_widget(tmp_path):
    """quote: the user selects matching text in an answer; the next message carries forwardedProps.reply_to."""
    (tmp_path / "q.yaml").write_text("name: q\npersona: p\ngoal: g\nturns: 3\nstart: {page: /apply, form: loan_application}\n"
                                     "quote: {pattern: 'Offline \\w+', ask: 'Where does this come from?'}\n")
    sc = evals.load_scenario(tmp_path / "q.yaml")
    sent = []
    http = evals.offline_client(tmp_path / "data")
    real = http.stream

    def spy(method, url, json=None, **kw):
        sent.append(json)
        return real(method, url, json=json, **kw)

    http.stream = spy
    out = evals.play(sc, http, None, None, offline=True)
    rt = [b["forwardedProps"]["reply_to"] for b in sent if (b.get("forwardedProps") or {}).get("reply_to")]
    assert rt and rt[0]["quote"] == "Offline answer" and rt[0]["message_id"]
    assert next(c for c in out["checks"] if c["check"] == "replies to a quote")["ok"]
    (tmp_path / "q.yaml").write_text("name: q\npersona: p\ngoal: g\nquote: {pattern: '(', ask: x}\n")
    with pytest.raises(evals.ScenarioError, match="not a regex"):
        evals.load_scenario(tmp_path / "q.yaml")


def test_expected_tools_are_counted_across_runs():
    run = lambda ok: {"name": "r", "score": 8.0, "min_score": 6, "checks": [{"check": "calls show_chart", "ok": ok}]}
    r = evals.combine([run(True), run(True), run(False)])
    assert r["tools_called"] == {"runs": 3, "ok": 2}
    text, _, _ = evals.summarize([r], None, 0.5)
    assert "tools 2/3" in text


def test_the_model_benchmark_swaps_only_the_agent_model(tmp_path):
    """--agent-model: the demo in-process from demo/formguide.yaml, with the agent's model replaced."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    class Fake(FakeListChatModel):
        def bind_tools(self, tools, **kw):  # type: ignore[override]
            return self

    http = evals.agent_client(tmp_path, Fake(responses=["Bench answer."] * 20))
    assert {p["path"] for p in http.get("/site/map").json()["pages"]} >= {"/", "/apply"}
    assert http.get("/lab/map").status_code == 200
    sc = next(s for s in evals.load_all() if s.name == "opening_hours")
    out = evals.play(sc, http, None, None, offline=True)
    assert not any(c["check"] in ("the scenario ran", "no run errors") and not c["ok"] for c in out["checks"]), out["checks"]


def test_a_reply_to_two_quotes_sends_a_list_with_notes(tmp_path):
    (tmp_path / "q.yaml").write_text("name: q\npersona: p\ngoal: g\nturns: 3\nstart: {page: /apply, form: loan_application}\n"
                                     "quote:\n  quotes: [{pattern: 'Offline', note: too high}, {pattern: 'answer'}]\n  ask: 'Better?'\n")
    sc = evals.load_scenario(tmp_path / "q.yaml")
    sent = []
    http = evals.offline_client(tmp_path / "data")
    real = http.stream
    http.stream = lambda m, u, json=None, **kw: (sent.append(json), real(m, u, json=json, **kw))[1]
    evals.play(sc, http, None, None, offline=True)
    rt = next(b["forwardedProps"]["reply_to"] for b in sent if (b.get("forwardedProps") or {}).get("reply_to"))
    assert [(q["quote"], q.get("note")) for q in rt] == [("Offline", "too high"), ("answer", None)]


def test_researcher_checks_never_tools_sources_corpus_and_gold(tmp_path):
    (tmp_path / "r.yaml").write_text("name: r\npersona: p\ngoal: g\ndocuments: northwind_insurance\ngold: 'The excess is 250 EUR.'\n"
                                     "start: {page: /insure, form: car_insurance}\n"
                                     "expect: {never_tools: [ask_documents], sources: ['policy.md > Excess']}\n")
    sc = evals.load_scenario(tmp_path / "r.yaml")
    assert sc.corpus == "northwind_insurance" and not sc.documents and sc.gold.startswith("The excess")

    class V:
        tools = [("ask_documents", {})]
        sources = [{"title": "policy.md", "section": "Excess"}]
        messages, cards, forms, errors, path = [], [], {}, [], "/insure"
        log: list = []
    out = {c["check"]: c["ok"] for c in evals.checks(sc, V())}
    assert out == {"never calls ask_documents": False, "cites policy.md > Excess": True}
