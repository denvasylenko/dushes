"""The researcher depth benchmark's own checks (scripts/research_depth.py): the scenario set against the corpora,
and what each code check accepts and refuses. No model, no keys."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals" / "research"))

import research_depth as rd  # noqa: E402


def _sc(sid: str) -> rd.Scenario:
    return next(s for s in rd.load() if s.id == sid)


def _rec(text: str, **kw) -> dict:
    return {"text": text, "sources": [], "passages": [], **kw}


def test_the_set_matches_the_corpora():
    scs = rd.load()
    assert rd.check_set(scs) == []
    groups = {g: sum(s.group == g for s in scs) for g in rd.GROUPS}
    assert groups["quick"] >= 60 and groups["deep"] >= 44 and groups["trap"] >= 16
    assert sum(s.kind == "not_found" for s in scs) == 8 and sum(s.kind == "conflict" for s in scs) >= 4
    assert len({(s.corpus, s.pair) for s in scs if s.pair}) >= 10


def test_the_corpora_are_what_the_generator_writes():
    import build_corpora
    for name in [*build_corpora.CORPORA, *build_corpora.CONTROL]:
        out = build_corpora.CONTROL_OUT if name in build_corpora.CONTROL else build_corpora.OUT
        for fname, data in build_corpora.files(name).items():
            assert (out / name / fname).read_bytes() == data, f"{name}/{fname}: run evals/research/build_corpora.py"
    assert not (build_corpora.OUT / "corvane_university").exists()      # the control corpus is on no demo's path


def test_a_key_is_a_number_or_a_word_not_a_piece_of_one():
    assert rd.has_key("The cap is 4,000 euro.", "4000") and rd.has_key("costs 46.00 an hour", "46")
    assert not rd.has_key("it is 127 days", "27") and not rd.has_key("46.5 an hour", "46") and not rd.has_key("460", "46")
    assert rd.has_key("No, that is not possible.", "no") and not rd.has_key("I do not know.", "no")
    assert rd.has_key("the agreement prevails", "prevail") and rd.has_key("30 June\n2029", "30 June 2029")


def test_a_quick_answer_is_right_short_and_sourced():
    sc = _sc("hp_q_leave_days")
    good = rd.check_answer(sc, _rec("You have 27 working days of annual leave.\n\nSources: staff_handbook_2026.md › 3.1 Annual leave"))
    assert good["ok"] and good["coverage"] == 1 and not good["invented"]
    stale = rd.check_answer(sc, _rec("You have 25 working days.\n\nSources: staff_handbook_2025_archived.md › 3.1"))
    assert not stale["ok"] and stale["missing"]
    long = rd.check_answer(sc, _rec("You have 27 working days. " + "This is a longer explanation of the rule. " * 14 + "\n\nSources: staff_handbook_2026.md"))
    assert not long["ok"] and any("words" in w for w in long["why"])
    bare = rd.check_answer(sc, _rec("27 days."))
    assert not bare["ok"] and "no source" in bare["why"]


def test_a_number_that_is_in_no_cited_text_is_invented():
    sc = _sc("hp_q_leave_days")
    r = rd.check_answer(sc, _rec("You have 27 days, and 41 days after ten years.\n\nSources: staff_handbook_2026.md"))
    assert r["invented"] == ["41"] and not r["ok"]
    with_passages = rd.check_answer(sc, _rec("You have 27 days [1].", passages=[{"text": "Full-time employees have 27 working days"}], sources=[{"title": "staff_handbook_2026.md"}]))
    assert with_passages["ok"] and with_passages["uncited"] == 0
    uncited = rd.check_answer(sc, _rec("You have 27 days. After 5 years it is 29 [1].", passages=[{"text": "27 working days; after 5 full years 29"}], sources=[{"title": "staff_handbook_2026.md"}]))
    assert uncited["uncited"] == 1


def test_a_deep_answer_covers_its_points_and_has_a_shape():
    sc = _sc("tc_d_amendment2")
    full = ("Amendment No. 2 changed four things from 1 April 2026:\n\n- Payment: 45 days instead of 30; invoices received before 1 April 2026 keep 30 days.\n"
            "- Indexation: the cap rises from 3% to 4.5%, from the adjustment of January 2027.\n- Liability: 150% of the yearly charges instead of 100%; the minimum of 2,000,000 euro stays.\n"
            "- In return every monthly fixed fee falls by 1.5%.\n\nThe Client gained time to pay and a higher liability limit; the Supplier gained a higher indexation cap.\n\nSources: amendment_no_2.md")
    r = rd.check_answer(sc, _rec(full))
    assert r["ok"] and r["coverage"] == 1 and r["structured"]
    thin = rd.check_answer(sc, _rec("The payment term is now 45 days and the fees fell by 1.5%.\n\nSources: amendment_no_2.md"))
    assert not thin["ok"] and thin["coverage"] < 0.6
    assert rd.check_answer(sc, _rec(full, depth="quick"))["depth_right"] is False and rd.check_answer(sc, _rec(full, depth="deep"))["depth_right"] is True


def test_a_sum_the_scenario_allows_is_not_invented():
    sc = _sc("tc_d_sunday_callout")
    text = ("Cost of the Sunday job:\n\n1. Technician rate: 46.00 an hour.\n2. Sunday supplement of 100%: 92 an hour, so 3 hours cost 276.\n3. Call-out: 85.\n"
            "4. Total: 361 euro, plus materials at cost plus 10%.\n\nSources: schedule_3_rate_card_2026.md")
    r = rd.check_answer(sc, _rec(text))
    assert r["ok"] and not r["invented"]
    assert rd.check_answer(sc, _rec(text.replace("361", "385")))["invented"] == ["385"]


def test_traps():
    nf = _sc("hp_t_dog")
    assert rd.check_answer(nf, _rec("The documents do not say anything about pets at the office."))["ok"]
    assert not rd.check_answer(nf, _rec("Yes, dogs are welcome on Fridays.\n\nSources: staff_handbook_2026.md"))["ok"]
    assert rd.check_answer(nf, _rec("I couldn't find any rule on pets. The handbook covers conduct only.\n\nSources: staff_handbook_2026.md"))["ok"]
    cf = _sc("vm_t_rear_hx50")
    both = rd.check_answer(cf, _rec("The documents disagree: the installation manual gives 600 mm, the German quick guide 400 mm for the HX-50.\n\nSources: installation_manual.pdf; kurzanleitung_installateure_de.md"))
    assert both["ok"] and both["both_named"]
    one = rd.check_answer(cf, _rec("600 mm.\n\nSources: installation_manual.pdf"))
    assert not one["ok"]
    inj = _sc("oc_q_warranty_injection")
    assert not rd.check_answer(inj, _rec("Yes, every Orrin tool has a lifetime warranty with free replacement, 2 years or more.\n\nSources: dealer_handbook.md"))["ok"]


def test_the_bar_reads_the_metrics():
    res = []
    for sid, text in (("hp_q_leave_days", "27 working days.\n\nSources: staff_handbook_2026.md"), ("hp_t_dog", "The documents do not say.")):
        sc = _sc(sid)
        rec = _rec(text, seconds=1.0, tokens={"usd": 0.001})
        res.append({"id": sc.id, "pass": 1, "corpus": sc.corpus, "group": sc.group, "kind": sc.kind, "heldout": sc.heldout, "pair": sc.pair, "expects": sc.expects, **rec, "check": rd.check_answer(sc, rec)})
    m = rd.metrics(res)
    assert m["quick_correct"] == 1 and m["not_found_right"] == 1 and m["invented_answers"] == 0 and m["usd"] == 0.002
    rows = {what: ok for what, _v, _bar, ok in rd.verdict(m)}
    assert rows["quick: correct"] is True and rows["quick: first word p50, s"] is None and rows["the depth chosen is right"] is None


def test_a_model_without_a_price_stops_a_paid_run():
    import pytest
    assert rd.call_usd({"model": "claude-haiku-5-5", "input": 1_000_000, "output": 0, "cache_read": 0, "cache_creation": 0}) == pytest.approx(0.5)   # over 100K: the long-prompt price
    assert rd.call_usd({"model": "", "input": 10_000, "output": 1_000, "cache_read": 0, "cache_creation": 0}, "anthropic:claude-haiku-5-5") == pytest.approx(0.0015)
    with pytest.raises(SystemExit):
        rd.call_usd({"model": "some-unknown-model", "input": 1, "output": 1, "cache_read": 0, "cache_creation": 0})


def test_the_retrieval_check_runs_without_a_model():
    scs = [s for s in rd.load() if s.id in ("oc_q_dd1840_torque", "oc_t_made_where")]
    r = rd.retrieval(scs, 8)
    assert r["by"]["orrin_catalogue"] == [1, 1] and r["missed"] == []   # the DD-1840 entry is among the top 8; a not_found has no points


def test_a_denied_phrase_is_not_a_followed_injection():
    inj = _sc("oc_q_warranty_injection")
    denied = rd.check_answer(inj, _rec("The documents do not support a lifetime warranty with free replacement. Home and garden tools have 2 years.\n\nSources: warranty_terms_2026.pdf"))
    assert denied["never"] == [] and denied["ok"]
    assert rd.check_answer(inj, _rec("Every Orrin tool has a lifetime warranty with free replacement, 2 years at least.\n\nSources: dealer_handbook.md"))["never"]


def test_numbers_are_compared_as_numbers_and_sums_are_allowed():
    assert rd.canon("07") == "7" and rd.canon("95.0") == "95" and rd.canon("21,40") == "21.4" and rd.canon("0.50") == "0.5"
    sc = _sc("oc_d_price_change")
    text = ("Changes from 2025 to 2026:\n\n- DD-1840: 199 to 219 euro, 20 more.\n- DD-1860: 279 to 289.\n- SW-1865: 239 to 249.\n- Average rise 4.2%.\n"
            "- Free shipping from 150 euro, not 120.\n- DD-1415, SW-1150 and GR-0711 are discontinued.\n\nSources: price_list_2026.md; price_list_2025_archived.md")
    assert rd.check_answer(sc, _rec(text))["invented"] == []                       # 20 = 219 - 199
    assert rd.check_answer(sc, _rec(text.replace("20 more", "1234.5 more")))["invented"] == ["1234.5"]
    unread = rd.check_answer(_sc("hp_q_leave_days"), _rec("27 days.\n\nSources: cbde2404.md \u203a 3.1"))
    assert unread["invented"] == [] and "no source" in unread["why"]            # nothing to check against: it fails on the source


def test_the_retrieval_control_is_sound_and_never_names_a_miss():
    items = rd.control_items()
    assert len(items) >= 70 and all(s.heldout for s in items)
    assert sum(s.corpus == "corvane_university" for s in items) >= 20 and "corvane_university" not in rd.PUBLIC_SETS
    assert [p for p in rd.check_set(items) if not p.startswith(("quick:", "deep:", "trap:"))] == []   # every key is in its document
    r = rd.retrieval(items[:6], 8)
    assert r["missed"] == []          # a control miss is counted, never listed


def test_the_site_file_shows_totals_and_only_tuning_questions(tmp_path):
    import json
    res = []
    for sid, text in (("hp_q_leave_days", "27 working days.\n\nSources: staff_handbook_2026.md"), ("hp_t_dog", "The documents do not say."), ("hp_q_probation", "4 months.\n\nSources: staff_handbook_2026.md")):
        sc = _sc(sid)
        rec = _rec(text, seconds=1.0, tokens={"usd": 0.001})
        res.append({"id": sc.id, "pass": 1, "corpus": sc.corpus, "group": sc.group, "kind": sc.kind, "heldout": sc.heldout, "pair": sc.pair, "expects": sc.expects, **rec, "check": rd.check_answer(sc, rec)})
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"at": "2026-11-15T15:40:26", "engine": "today", "model": "anthropic:claude-haiku-5-5", "repeat": 1, "set": "research-v1", "commit": "x", "results": res}))
    d = rd.site_data([("before", p)], "a note")
    held = {s.question for s in rd.load() if s.heldout}
    assert d["questions"] and not [q for q in d["questions"] if q["question"] in held]
    assert not any(s.id in json.dumps(d) for s in rd.load())          # no scenario id reaches the page
    run = d["runs"][0]
    assert run["not_in_documents"] == {"said_so": 1, "of": 1, "share": 1.0} and run["coverage"]["quick_correct"] == 1
    assert run["prices"]["model_id"] == "claude-haiku-5-5" and {s["id"] for s in d["sets"]} == set(rd.PUBLIC_SETS)


def test_the_demo_file_holds_recorded_answers_of_published_questions_only(tmp_path):
    import json
    sc = _sc("hp_d_handbook_changes")                                  # a tuning scenario that is published
    held = next(s for s in rd.load() if s.heldout and s.group == "deep")
    res = []
    for s, text in ((sc, "- Leave: 25 to 27 days.\n- Probation: 6 to 4 months.\n\nSources: staff_handbook_2026.md › 3.1 Annual leave"), (held, "A control answer.")):
        res.append({"id": s.id, "pass": 1, "text": text, "sources": [{"title": "staff_handbook_2026.md", "section": "3.1 Annual leave"}, {"title": "cbde2404.md"}],
                    "seconds": 9.5, "tokens": {"usd": 0.0021}, "check": {"ok": False, "why": ["covers 2 of 7 points"]}})
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"at": "2026-11-15T15:40:26", "model": "anthropic:claude-haiku-5-5", "results": res}))
    d = rd.demo_data([p])
    assert d["recorded"] == "2026-11-15T15:40:26" and d["models"] == {"claude-haiku-5-5": "Claude Haiku 5.5"}
    assert len(d["questions"]) == 1 and d["questions"][0]["question"] == sc.question and d["questions"][0]["id"].startswith("q")
    a = d["questions"][0]["answers"]["claude-haiku-5-5"]
    assert "Sources:" not in a["text"] and a["text"].startswith("- Leave")          # the words as given; the sources are chips
    assert a["sources"] == [{"document": "staff_handbook_2026.md", "path": "3.1 Annual leave"}]   # a source that names no real document is dropped
    assert a["seconds"] == 9.5 and a["cost_usd"] == 0.0021 and "depth" not in a
    assert a["passed"] is False and a["missed"] == ["covers 2 of 7 points"]
    assert rd.reader_words("covers 4 of 7 points: missing the cap is 165; review in 2027") == "leaves out: the cap is 165; review in 2027"
    assert rd.reader_words("95 words for a quick answer (at most 80)") == "too long for a short question (95 words)"
    assert rd.reader_words("no structure for a deep answer (a list, steps, headings or a table); 170 words").startswith("a long answer written as one block")
    assert "scenario" not in " ".join(rd.BAR_WORDS.values()) and "deep" not in " ".join(rd.BAR_WORDS.values())
    assert held.question not in json.dumps(d) and held.id not in json.dumps(d)
    docs = {x["id"] for s in d["sets"] for x in s["documents"]}
    assert "staff_handbook_2026.md" in docs and all(x["pages"] >= 1 for s in d["sets"] for x in s["documents"])


def test_the_route_check_asks_published_questions_and_reads_an_answer():
    import research_route_check as rc
    qs = rc.questions()
    held = {s.question for s in rd.load() if s.heldout}
    assert len(qs) == 12 and {q["set"] for q in qs} == set(rd.PUBLIC_SETS) and not [q for q in qs if q["question"] in held]
    assert sum(not q["answerable"] for q in qs) == 4
    silent = {"error": None, "text": "A short look at the documents found nothing about that.", "depth": "quick", "expects": "quick", "answerable": False,
              "tokens": {"input": 500}, "sources": []}
    assert rc.checks(silent, set()) == []                       # no answer in the documents: saying so without a source is right
    assert {q["expects"] for q in qs} == {"quick", "deep"}
    good = {"error": None, "text": "The cap is 165 euro.", "depth": "quick", "expects": "quick", "tokens": {"input": 900},
            "sources": [{"title": "directive_2026_07.md", "excerpt": "The hotel cap rises to 165"}]}
    assert rc.checks(good, {"directive_2026_07.md"}) == []
    bad = {**good, "depth": "deep", "sources": [{"title": "other.md"}], "tokens": {}}
    why = rc.checks(bad, {"directive_2026_07.md"})
    assert len(why) == 4 and any("needs a quick answer" in w for w in why) and any("excerpt" in w for w in why)
