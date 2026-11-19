"""`formguide check`: what is weak in a host's description of its site and forms, and how to fix it. No model call."""
from __future__ import annotations

import dataclasses
import json

from formguide import advice
from formguide.cli import main
from formguide.form.layout import LayoutIndex
from formguide.site import SiteMap

from .test_agent import LOAN

SITE = {"title": "Shop", "pages": [
    {"path": "/", "title": "Home"},
    {"path": "/loans", "title": "Loans", "keywords": ["loan"], "form": "loan_application",
     "sections": [{"id": "rates", "title": "Rates", "text": "x"}]},
    {"path": "/rates", "title": "Rates", "keywords": ["rates", "Zinsen", "tassi"]},
]}


def test_the_site_map_keywords_titles_and_forms_without_documents():
    found = advice.check_site(SiteMap.load(SITE), ["en", "de", "it"], documents_for=lambda form_id: [])
    by = {(f.level, f.where): f for f in found}
    assert "no keywords" in by[("warning", "site /")].what
    assert "1 keyword(s) for a site in 3 languages" in by[("warning", "site /loans")].what
    assert not any(f.where == "site /rates" for f in found)                         # three keywords for three languages
    same = next(f for f in found if f.where == "site" and "same title" in f.what)
    assert "/loans#rates" in same.what and "/rates" in same.what
    assert any(f.level == "note" and "no business documents" in f.what for f in found)
    assert all(f.fix for f in found)                                                # every finding says what to do
    one = advice.check_site(SiteMap.load(SITE), ["en"], documents_for=lambda form_id: ["tariffs.md"])
    assert not any("languages" in f.what or "documents" in f.what for f in one)     # one language, documents there


def test_a_form_labels_options_personal_fields_and_required_ones(guide):
    lay = LayoutIndex(LOAN.jsx)
    config = LOAN.compute(None)
    pack = guide.packs.get("loan_application")
    bare = advice.check_form("loan_application", lay, config, dataclasses.replace(pack, pii=set(), glossary={}))
    errors = {f.where.split(": ")[1]: f for f in bare if f.level == "error"}
    assert "phone_mobile" in errors and "email" in errors and "a phone number" in errors["phone_mobile"].what
    warned = {f.where.split(": ")[1] for f in bare if f.level == "warning" and "identity document" in f.what}
    assert "passport_number" in warned and "passport_number" not in errors          # may be a company's: to look at
    everything = {f.where.split(": ")[1] for f in bare if "does not mark it" in f.what}
    marked = advice.check_form("loan_application", lay, config, dataclasses.replace(pack, pii=everything))
    assert not any("does not mark it" in f.what for f in marked)                    # once marked, nothing is said
    assert any(f.level == "note" and "required field(s) have no note" in f.what for f in bare)
    # a label that is the field's own name, and an option with no name to show
    odd = json.loads(json.dumps(config))
    odd["props"]["first_name"]["label"] = "first_name"
    found = advice.check_form("loan_application", lay, odd, pack)
    assert any(f.where.endswith(": first_name") and "identifier" in f.what for f in found)
    assert advice._technical("", "x") and advice._technical("loanAmount", "x") and not advice._technical("Loan amount", "x")


def test_the_environment_what_is_not_for_a_public_host():
    env = {"INTENT_PROVIDER": "jev", "INTENT_API_KEY": "k", "INTENT_LABELS": "1", "INTENT_TRACE": "1"}
    local = advice.check_environment(env, public=False)
    assert [f.level for f in local if "INTENT_LABELS" in f.what] == ["warning"]
    public = advice.check_environment(env, public=True)
    assert [f.level for f in public if "INTENT_LABELS" in f.what] == ["error"]
    assert any("no access codes" in f.what for f in public)
    assert advice.check_environment({}, public=True) == [] and advice.render([]) == "nothing weak found"
    assert any("INTENT_API_KEY" in f.what for f in advice.check_environment({"INTENT_PROVIDER": "jev"}, True))


def test_the_command_fails_on_an_error_so_a_coding_agent_sees_it(tmp_path, monkeypatch, capsys):
    (tmp_path / "formguide.yaml").write_text("languages: [en, de]\n")
    (tmp_path / "site.yaml").write_text(json.dumps(SITE))
    for name in ("INTENT_LABELS", "INTENT_TRACE", "INTENT_SCORES", "INTENT_PROVIDER", "EXPERIMENT_CODES", "JOURNAL", "VOICE_CODES"):
        monkeypatch.delenv(name, raising=False)
    args = ["check", "--config", str(tmp_path / "formguide.yaml"), "--site", str(tmp_path / "site.yaml")]
    assert main(args) == 0                                                          # warnings only: it still passes
    out = capsys.readouterr().out
    assert "WARNING site /" in out and "fix: add `keywords:`" in out and out.rstrip().endswith("OK")
    monkeypatch.setenv("INTENT_LABELS", "1")
    assert main([*args, "--public"]) == 1                                           # an error: the exit code says so
    assert "ERROR   environment" in capsys.readouterr().out
