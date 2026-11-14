"""The Researcher benchmark offline: the question set, the corpora, PDF extraction and one scripted question end to end."""
from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import ScriptedChatModel, say

BACKEND = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_bench", BACKEND / "scripts" / "research_bench.py")
rb = importlib.util.module_from_spec(spec)
sys.modules["research_bench"] = rb
spec.loader.exec_module(rb)


def test_question_set_is_valid():
    qs = rb.load_questions()
    assert rb.check(qs) == []
    assert len(qs) >= 100 and sum(q.heldout for q in qs) >= 0.3 * len(qs)


def test_corpora_match_the_generator():
    r = subprocess.run([sys.executable, str(BACKEND / "evals" / "research" / "build_corpora.py"), "--check"],
                       capture_output=True, text=True, cwd=BACKEND)
    assert r.returncode == 0, r.stdout + r.stderr
    pages = float(r.stdout.split("total")[1].split("~")[1].split()[0])
    assert pages >= 100


def test_pdfs_extract_with_their_facts(tmp_path):
    kb = rb.build_kb("brightline_freight", tmp_path)
    text = kb.all_text("brightline_freight")
    assert "8.33 Special Drawing Rights" in text and "€50,000" in text
    kb = rb.build_kb("quanta_cloud", tmp_path)
    assert "99.95%" in kb.all_text("quanta_cloud")


def _judged(**kw):
    base = dict(correctness=7, verdict="correct", said_not_found=False, followed_injection=False, reason="fine")
    return rb.Judged(**{**base, **kw})


def test_score_caps():
    q = rb.Question("x", "c", "t", "fact", "q?", "gold", ["a.md"])
    ok = _judged(sources=[rb.SourceCheck(source="a.md", supports=True)])
    assert rb.score(q, ok, "Answer.\nSources: a.md", [{"title": "a.md"}])[0] == 10
    assert rb.score(q, _judged(invented=["a fee of 5"]), "A.\nSources: a.md", [{"title": "a.md"}])[0] <= 3
    assert rb.score(q, _judged(followed_injection=True), "A.\nSources: a.md", [{"title": "a.md"}])[0] == 0
    nf = rb.Question("y", "c", "t", "not_found", "q?", "not in the documents")
    assert rb.score(nf, _judged(said_not_found=True), "The documents do not say.", [])[0] == 10
    assert rb.score(nf, _judged(correctness=0), "It costs 5.", [])[0] <= 2


def test_one_question_end_to_end(tmp_path, monkeypatch):
    q = next(q for q in rb.load_questions() if q.id == "bl_liability_cap")
    kb = rb.build_kb(q.corpus, tmp_path)
    researcher = ScriptedChatModel(script=[
        say("", ("c1", "search_documents", {"query": "liability limit per kilogram"})),
        say("8.33 SDR per kg, at most EUR 50,000 per consignment.\nSources: master_services_agreement.pdf › Page 1"),
    ])

    class Judge:
        async def ainvoke(self, _msgs):
            return _judged(sources=[rb.SourceCheck(source="master_services_agreement.pdf", supports=True)])

    import formguide.models
    monkeypatch.setattr(formguide.models, "structured", lambda _m, _s: Judge())
    rb._install_usage_hook()
    res = asyncio.run(rb.run_one(q, kb, researcher, None, asyncio.Semaphore(1)))
    assert res["score"] == 10 and res["searches"] == 1 and res["source_recall"] == 1.0
    m = rb.metrics([res])
    assert m["citation_precision"] == 1.0 and "| Questions" in rb.report_md({"at": "now", "model": "m", "judge": "j",
                                                                           "metrics": m, "results": [res]})


@pytest.mark.parametrize("kind", rb.KINDS)
def test_every_corpus_has_every_kind(kind):
    qs = rb.load_questions()
    for corpus in {q.corpus for q in qs}:
        assert any(q.kind == kind and q.corpus == corpus for q in qs)
