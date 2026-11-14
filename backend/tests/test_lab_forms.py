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


def test_the_assistant_does_not_act_dumb_checks():
    sc = evals.Scenario(name="x", persona="p", goal="g", never_repeat_questions=True, never_suggests=["Pick a day"],
                        never_says_after_card=["pick a day"], rejected_values={"phone": "333"}, never_numbers=["8"])

    class F:
        config = {"props": {"phone": {}}, "state": {"phone": "333"}}

    class V:
        cards = [{"type": "ask", "question": "Which day?", "field": "day"},
                 {"type": "set_fields", "changes": [{"name": "day", "value": "2026-12-01"}]},
                 {"type": "ask", "question": "Which  day?", "field": "day"}]
        suggestions = [["Pick a day", "Thanks"]]
        log = ["🤖 Which day?", "   🃏 card shown and accepted by the user (the form now has these values): Day = 1 Dec", "🤖 Booked. Now pick a day."]
        messages = [{"role": "assistant", "content": "You had 8 visits"}, {"role": "assistant", "content": "Booked. Now pick a day."}]
        forms = {"f": F()}
        tools, sources, errors, path = [], [], [], "/"
    out = {c["check"]: c["ok"] for c in evals.checks(sc, V())}
    assert out == {"never repeats a question": False, "never suggests Pick a day": False, "never says pick a day after a card": False,
                   "phone does not keep 333": False, "never states the number 8": False}
    V.messages = [{"role": "assistant", "content": "You had 2 visits, 18 views and 8.5 stars"}]
    assert next(c for c in evals.checks(sc, V()) if c["check"] == "never states the number 8")["ok"]


def test_another_hosts_headers_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("FORMGUIDE_COOKIE", "hf_cab=abc")
    monkeypatch.setenv("FORMGUIDE_HEADERS", '{"X-Site": "1"}')
    assert evals.host_headers() == {"X-Site": "1", "Cookie": "hf_cab=abc"}
    monkeypatch.delenv("FORMGUIDE_COOKIE"); monkeypatch.delenv("FORMGUIDE_HEADERS")
    assert evals.host_headers() == {}


def test_a_scenario_folder_from_the_command_line(tmp_path, monkeypatch):
    (tmp_path / "one.yaml").write_text("name: one\npersona: p\ngoal: g\nturns: 1\n")
    seen = {}
    monkeypatch.setattr(evals, "run", lambda names, **kw: (seen.update(kw), ({}, False))[1])
    assert evals.main(["--offline", "--folder", str(tmp_path)]) == 0
    assert seen["folder"] == tmp_path and seen["baseline_file"] == tmp_path / "baseline.json"


def test_a_host_form_with_its_own_hash_and_a_wrapped_apply(monkeypatch):
    import harness_client as hc

    class R:
        def __init__(self, body): self.body, self.status_code, self.headers, self.request = body, 200, {}, None
        def raise_for_status(self): return self
        def json(self): return self.body

    calls = []

    class H:
        def get(self, url, params=None): calls.append(("GET", url)); return R({"config": {"props": {}, "state": {"a": 1}}, "jsx_hash": "h1"})
        def post(self, url, json=None): calls.append(("POST", url)); return R({"config": {"props": {}, "state": {"a": 2}}, "changed": ["a"]})
    f = hc.Form(H(), "x")
    assert f.hash == "h1" and calls == [("GET", hc.FORM_URL)]          # no layout registration
    f.apply({"a": 2})
    assert f.config == {"props": {}, "state": {"a": 2}}


def test_a_preset_picker_is_caught():
    sc = evals.Scenario(name="x", persona="p", goal="g", never_preset_pickers=True)

    class V:
        cards = [{"type": "ask", "question": "Licence year?", "input": {"type": "number", "min": 2026, "max": 2026, "value": 1988}}]
        messages, forms, tools, sources, errors, log, path = [], {}, [], [], [], [], "/"
    assert not next(c for c in evals.checks(sc, V()) if c["check"] == "never presets a picker")["ok"]
    V.cards = [{"type": "ask", "question": "Licence year?", "input": {"type": "number", "min": 2026, "max": 2026}}]
    assert next(c for c in evals.checks(sc, V()) if c["check"] == "never presets a picker")["ok"]


def test_cards_in_the_users_language():
    sc = evals.Scenario(name="x", persona="p", goal="g", never_ask_words=["Consumer loan", "Mortgage"], never_fill_words=["Loan type"])

    class V:
        cards = [{"type": "ask", "question": "Quale prestito?", "options": [{"id": "consumer", "label": "Prestito personale"}, {"id": "mortgage", "label": "Mortgage"}]},
                 {"type": "set_fields", "changes": [{"name": "loan_type", "label": "Loan type", "display": "Prestito personale"}]}]
        messages, forms, tools, sources, errors, log, path = [], {}, [], [], [], [], "/"
    ok = {c["check"]: c["ok"] for c in evals.checks(sc, V())}
    assert ok == {"no question card shows Consumer loan": True, "no question card shows Mortgage": False,
                  "no field-change card shows Loan type": False}


def test_cards_in_language_derives_the_english_from_the_form():
    sc = evals.Scenario(name="x", persona="p", goal="g", cards_in_language=True, plain_numbers=["year"])

    class F:
        config = {"props": {"year": {"label": "Year of manufacture"}, "make": {"label": "Make", "options": [{"id": "toyota", "name": "Toyota"}]},
                            "usage": {"label": "How the car is used", "options": [{"id": "commute", "name": "Commuting to work"}]}}, "state": {}}

    class V:
        cards = [{"type": "set_fields", "changes": [{"name": "year", "label": "Year of manufacture", "display": "2,019", "reason": "given by the user"},
                                                    {"name": "make", "label": "Marke", "display": "Toyota"}]}]
        messages, tools, sources, errors, log, path = [], [], [], [], [], "/"
        forms = {"f": F()}
    ok = {c["check"]: c for c in evals.checks(sc, V())}
    assert not ok["cards are in the user's language"]["ok"] and "Year of manufacture" in ok["cards are in the user's language"]["detail"]
    assert "Toyota" not in ok["cards are in the user's language"]["detail"]   # a one-word brand is the same in every language
    assert not ok["year shows without a thousands separator"]["ok"]
    V.cards = [{"type": "set_fields", "changes": [{"name": "year", "label": "Baujahr", "display": "2019", "reason": "von Ihnen genannt"}]}]
    ok = {c["check"]: c["ok"] for c in evals.checks(sc, V())}
    assert ok["cards are in the user's language"] and ok["year shows without a thousands separator"]


def test_a_quote_of_the_users_own_message_is_sent_with_the_user_role(tmp_path):
    """quote item `from: user`: the text is selected in the user's own message; reply_to carries role "user"."""
    import evals
    from harness_client import Visit
    q = evals._quote(tmp_path / "q.yaml", {"quotes": [{"pattern": "500 000", "from": "user"}], "ask": "make it 300 000"})
    v = Visit.__new__(Visit)
    v.said, v.replies = [("user-1", "I want 500 000 for 36 months")], [("a1", "500 000 over 36 months it is.")]
    assert evals.find_quotes(v, q) == [{"message_id": "user-1", "quote": "500 000", "role": "user"}]
    assert evals.find_quote(v, "500 000") == {"message_id": "a1", "quote": "500 000"}
    with pytest.raises(evals.ScenarioError):
        evals._quote(tmp_path / "q.yaml", {"quotes": [{"pattern": "x", "from": "assistant"}], "ask": "y"})
    assert evals.load_scenario(evals.EVALS / "quote_own_message_amount.yaml").quote["items"][0]["from"] == "user"


def test_ask_ai_highlight_not_a_duplicate_is_checked_in_code():
    import ask_ai_evals as aa
    card = {"id": "card_aaaaaaaa", "blocks": [{"code": "x"}]}
    ok = lambda checks: [c["ok"] for c in checks]
    first = {"cards": [card], "highlights": []}
    hl = {"highlights_first_card": True}
    assert ok(aa.highlight_checks(hl, [first, {"cards": [], "highlights": [{"card_id": "card_aaaaaaaa"}]}])) == [True, True, True]
    assert ok(aa.highlight_checks(hl, [first, {"cards": [{**card, "id": "card_bbbbbbbb"}], "highlights": []}])) == [True, False, False]
    assert ok(aa.highlight_checks(hl, [{"cards": [{"blocks": []}], "highlights": []}, {"cards": [], "highlights": []}]))[0] is False
    new = {"new_card_no_highlight": True}
    assert ok(aa.highlight_checks(new, [first, {"cards": [{**card, "id": "card_bbbbbbbb"}], "highlights": []}])) == [True, True]
    assert ok(aa.highlight_checks(new, [first, {"cards": [], "highlights": [{"card_id": "card_aaaaaaaa"}]}])) == [False, False]
    assert {q["name"] for q in aa.load()} >= {"show_again_highlights", "show_again_far_up_new_card"}
