"""Reading the conversation log by time, the judge's rubric, and deleting old conversations."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from formguide import judge
from formguide.transcript import FileTranscriptStore, MemoryTranscriptStore, new_entry

NOW = datetime.now(timezone.utc)


def at(kind, hours_ago, **kw):
    return {**new_entry(kind, **kw), "ts": (NOW - timedelta(hours=hours_ago)).isoformat(timespec="seconds")}


def test_stores_list_threads_by_time(tmp_path):
    mem = MemoryTranscriptStore()
    mem.append("old", at("user", 50, text="x"))
    mem.append("new", at("user", 1, text="y"))
    assert mem.threads() == ["new", "old"] and mem.threads(NOW - timedelta(hours=24)) == ["new"]
    files = FileTranscriptStore(tmp_path)
    files.append("old", at("user", 50, text="x"))
    files.append("new", at("user", 1, text="y"))
    past = (NOW - timedelta(hours=50)).timestamp()
    os.utime(tmp_path / "old.jsonl", (past, past))
    assert files.threads() == ["new", "old"] and files.threads(NOW - timedelta(hours=24)) == ["new"]


def test_a_days_conversations_with_the_form_thread_folded_in(guide):
    tx = guide.transcripts
    tx.append("s1", at("user", 3, text="where are you?"))
    tx.append("s1", at("assistant", 3, text="Main Street 1."))
    tx.append("s1", at("user", 2, text="a car loan", form_id="loan"))              # the site's copy of a form turn
    tx.append("s1", at("assistant", 2, text="Here is the card.", form_id="loan"))
    tx.append("s1-loan", at("user", 2, text="a car loan"))
    tx.append("s1-loan", at("tool", 2, name="propose_changes"))
    tx.append("s1-loan", at("assistant", 2, text="Here is the card."))
    tx.append("alone", at("user", 30, text="yesterday"))
    tx.append("alone", at("user", 1, text="today"))
    got = list(guide.conversations(NOW - timedelta(hours=24)))
    assert [c["thread_id"] for c in got] == ["alone", "s1"]                         # the form thread is not listed twice
    assert [e["text"] for e in got[0]["entries"]] == ["today"]                      # only the window
    s1 = got[1]["entries"]
    assert [(e["agent"], e["kind"]) for e in s1] == [("site", "user"), ("site", "assistant"), ("form", "user"),
                                                     ("form", "tool"), ("form", "assistant")]
    until = list(guide.conversations(NOW - timedelta(hours=24), NOW - timedelta(hours=2, minutes=30)))
    assert [len(c["entries"]) for c in until] == [2]                                # s1's first two entries only
    raw = {c["thread_id"] for c in guide.conversations(NOW - timedelta(hours=24), merge=False)}
    assert raw == {"alone", "s1", "s1-loan"}


def test_purge_counts_then_deletes_with_the_attachments(guide):
    tx = guide.transcripts
    tx.append("ancient", at("user", 24 * 400, text="x"))
    tx.append("fresh", at("user", 1, text="y"))
    guide.attachments.save("ancient", "a.txt", b"hello")
    assert asyncio.run(guide.purge(365, dry_run=True)) == 1 and tx.list("ancient")   # counted, not deleted
    assert asyncio.run(guide.purge(365)) == 1
    assert tx.list("ancient") == [] and tx.list("fresh")
    assert not (guide.attachments.root / "ancient").exists()


# the rubric's text by version: a changed text needs a new version (and a new line here), or old and new scores
# would look comparable
RUBRICS = {"2026-11-15": "1f2270c41060dc12"}


def test_the_rubric_text_cannot_change_without_its_version():
    import hashlib
    assert judge.RUBRIC.startswith("Score the assistant from 0 to 10")
    assert RUBRICS.get(judge.RUBRIC_VERSION) == hashlib.sha256(judge.RUBRIC.encode()).hexdigest()[:16], \
        "the rubric text changed: set a new RUBRIC_VERSION and add its hash to RUBRICS"
