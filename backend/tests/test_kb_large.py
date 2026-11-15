"""Retrieval for large documents: sections with their path and page, the prebuilt index, ranking across a mixed
set, the outline and neighbours, an older chunks.json. No model anywhere; the corpora are generated."""
from __future__ import annotations

import json
import time

from formguide.knowledge.base import KnowledgeBase, _spread
from formguide.knowledge.index import BM25Index, Chunk, stems
from formguide.knowledge.store import FORMAT, chunk_text

from .kb_corpus import handbook

DOC = """# Tariffs 2026

Intro line about the tariffs.

## 4 Fees

### 4.1 Monthly fee

The monthly fee is 12,50 EUR.

### 4.2 Late payment

A late payment costs 27,90 EUR after the reminder under clause 7.3.

| Days late | Charge |
| --- | --- |
| 1 to 10 | 5,00 |
| 11 to 30 | 27,90 |

## 5 Cancelling

- write to the office
- wait for the confirmation
- return the card
"""


def test_sections_keep_their_heading_path_and_order():
    chunks = chunk_text("ns", "d1", DOC)
    late = next(c for c in chunks if c.section == "4.2 Late payment")
    assert late.path == "4 Fees > 4.2 Late payment" and late.title == "Tariffs 2026"
    assert "| 11 to 30 | 27,90 |" in late.text and "A late payment costs" in late.text      # the table is with its text
    assert [c.order for c in chunks] == list(range(len(chunks)))
    assert next(c for c in chunks if c.section == "5 Cancelling").text.count("\n- ") == 2  # the list is whole
    assert chunks[0].path == "Tariffs 2026"                                                # text before any heading


def test_long_sections_overlap_and_tables_stay_whole():
    para = " ".join(f"Sentence number {i} of the long section." for i in range(120))
    table = "\n".join(["| a | b |", "| --- | --- |"] + [f"| row {i} | {i},50 |" for i in range(60)])
    chunks = chunk_text("ns", "d2", f"# Doc\n\n## Part\n\n{para}\n\n{table}\n", chunk_chars=1200, overlap=150)
    text = [c for c in chunks if "Sentence number" in c.text]
    assert len(text) >= 3 and all(len(c.text) <= 1500 for c in text)
    for a, b in zip(text, text[1:]):
        assert b.text[:40] in a.text                                    # the next section starts inside the one before
    assert sum("| row 0 |" in c.text and "| row 59 |" in c.text for c in chunks) == 1   # 1.4k characters, one piece
    assert all(c.path == "Part" for c in chunks)


def test_a_pdf_keeps_pages_and_numbered_headings():
    text, facts = handbook("Staff handbook", 40, seed=3, pdf=True)
    chunks = chunk_text("ns", "d3", text)
    found = [(f, next(c for c in chunks if f["sentence"] in c.text)) for f in facts]
    assert all(c.section == f["heading"] and c.path.endswith(f["heading"]) and " > " in c.path for f, c in found)
    assert sum(c.page > 1 for _f, c in found) > len(found) * 0.8
    assert not any(c.section.startswith("Page ") for c in chunks)
    assert max(c.page for c in chunks) >= 35


def test_figures_and_clause_numbers_are_found_as_written():
    assert {"27,90", "27.90", "4.2", "de89"} <= set(stems("Clause 4.2: pay 27,90 to DE89 3704"))
    idx = BM25Index()
    idx.add(chunk_text("ns", "d1", DOC))
    assert idx.search(["ns"], "27,90", 3)[0][1].section == "4.2 Late payment"
    assert idx.search(["ns"], "what does clause 7.3 say", 3)[0][1].section == "4.2 Late payment"
    assert idx.search(["ns"], "12.50", 3)[0][1].section == "4.1 Monthly fee"         # a dot for the comma


def test_a_heading_match_outranks_a_passing_mention():
    idx = BM25Index()
    idx.add(chunk_text("ns", "d1", DOC + "\n## 9 Other\n\nLate payment is mentioned here once, among other things "
                                         "that the office does on a normal day of work.\n"))
    assert idx.search(["ns"], "late payment", 2)[0][1].section == "4.2 Late payment"


def test_results_are_spread_over_documents():
    def hit(score, doc, n):
        return (score, Chunk(f"{doc}#{n}", "ns", doc, doc, "s", "t", path="s", order=n))
    hits = [hit(10 - i * 0.1, "a", i) for i in range(8)] + [hit(8.0, "b", 0), hit(7.9, "b", 1)]
    hits.sort(key=lambda x: -x[0])
    top = _spread(hits, 6, 4)
    assert [c.doc_id for _s, c in top].count("a") == 4 and [c.doc_id for _s, c in top].count("b") == 2
    alone = hits[:8] + [hit(1.0, "b", 0)]                              # the other document is far behind: no cap
    assert all(c.doc_id == "a" for _s, c in _spread(alone, 6, 4))


def test_outline_and_neighbours(tmp_path):
    kb = KnowledgeBase(tmp_path)
    kb.add_document("ns", "tariffs.md", DOC.encode())
    (doc,) = kb.outline("ns")
    assert doc["title"] == "tariffs.md" and doc["chars"] > 200
    # the store puts the file name first, so the document's own title line is the top of every path
    assert [h["path"] for h in doc["headings"]][1:4] == [
        "Tariffs 2026 > 4 Fees > 4.1 Monthly fee", "Tariffs 2026 > 4 Fees > 4.2 Late payment",
        "Tariffs 2026 > 5 Cancelling"]
    late = next(c for _s, c in kb.search("ns", "late payment") if c.section == "4.2 Late payment")
    around = kb.neighbours("ns", late.id)
    assert [c.section for c in around] == ["4.1 Monthly fee", "4.2 Late payment", "5 Cancelling"]
    assert kb.section("ns", late.id) is late or kb.section("ns", late.id).id == late.id


def test_an_older_chunks_file_is_cut_again_on_start(tmp_path):
    kb = KnowledgeBase(tmp_path)
    kb.add_document("ns", "tariffs.md", DOC.encode())
    p = tmp_path / "ns" / "chunks.json"
    old = [{"id": "x#0", "doc_id": "x", "title": "Old", "section": "Old", "text": "old text"}]   # before paths
    p.write_text(json.dumps(old))
    again = KnowledgeBase(tmp_path)
    data = json.loads(p.read_text())
    assert data["format"] == FORMAT and all("path" in c for c in data["chunks"])
    assert again.search("ns", "late payment")[0][1].path == "Tariffs 2026 > 4 Fees > 4.2 Late payment"
    assert not again.search("ns", "old text")                              # the old sections are gone


class _Vectors:
    """A stand-in for a vector index: it "understands" one paraphrase and knows nothing of figures."""
    ephemeral = False

    def __init__(self):
        self.chunks: dict[str, Chunk] = {}

    def add(self, chunks):
        self.chunks.update({c.id: c for c in chunks})

    def delete(self, chunks):
        for c in chunks:
            self.chunks.pop(c.id, None)

    def search(self, namespaces, query, k):
        want = "5 Cancelling" if "stop my contract" in query else None
        return [(0.9, c) for c in self.chunks.values() if c.section == want][:k]


def test_a_vector_index_is_fused_with_the_words(tmp_path):
    kb = KnowledgeBase(tmp_path, index=_Vectors())
    kb.add_document("ns", "tariffs.md", DOC.encode())
    assert kb.search("ns", "how do I stop my contract")[0][1].section == "5 Cancelling"     # only the vectors know
    assert kb.search("ns", "27,90")[0][1].section == "4.2 Late payment"                     # only the words know


# ---------------------------------------------------------------- the benchmark on large documents


def _library(tmp_path, sizes):
    kb = KnowledgeBase(tmp_path)
    facts = []
    for i, pages in enumerate(sizes):
        name = f"Handbook {chr(65 + i)}"
        text, planted = handbook(name, pages, seed=10 + i, pdf=i % 2 == 1)
        kb.add_document("lib", f"handbook_{chr(97 + i)}.md", text.encode())
        facts += planted
    return kb, facts


def _recall(kb, facts, question, k):
    found = 0
    for f in facts:
        hits = kb.search("lib", question(f), k)
        found += any(f["sentence"] in c.text for _s, c in hits)
    return found / len(facts)


def test_recall_on_100_300_and_500_pages(tmp_path):
    for sizes in ((100,), (300,), (200, 150, 100, 50)):                    # the last: 500 pages, a mixed set
        kb, facts = _library(tmp_path / str(sum(sizes)), sizes)
        pages = sum(d["chars"] for d in kb.outline("lib")) / 2400
        assert pages > sum(sizes) * 0.8, pages
        exact = _recall(kb, facts, lambda f: f"where is {f['figure']} EUR charged", 6)
        named = _recall(kb, facts, lambda f: f"how much do {f['topic']} cost per month in {f['name']}?", 6)
        loose = _recall(kb, facts, lambda f: f"monthly price of {f['topic'].split()[0]} ({f['name']})", 8)
        assert exact >= 0.97 and named >= 0.97 and loose >= 0.93, (sizes, exact, named, loose)   # first run: 1.00, 1.00, 0.99


def test_two_documents_answer_one_question(tmp_path):
    kb, facts = _library(tmp_path, (120, 120))
    by_topic: dict[str, list[dict]] = {}
    for f in facts:
        by_topic.setdefault(f["topic"], []).append(f)
    both = 0
    for topic, pair in by_topic.items():
        hits = kb.search("lib", f"compare the charge for {topic} in Handbook A and Handbook B", 8)
        both += all(any(f["sentence"] in c.text for _s, c in hits) for f in pair)
    assert both / len(by_topic) >= 0.9, both / len(by_topic)


def test_a_search_on_500_pages_is_fast(tmp_path):
    kb, facts = _library(tmp_path, (200, 150, 100, 50))
    questions = [f"how much do {f['topic']} cost per month in {f['name']}?" for f in facts[:40]]
    kb.search("lib", questions[0])
    times = []
    for q in questions:
        t = time.perf_counter()
        kb.search("lib", q, 8)
        times.append(time.perf_counter() - t)
    times.sort()
    assert times[len(times) // 2] < 0.05, times[len(times) // 2]           # the median, in seconds
