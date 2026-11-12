"""Richer field-change cards: field kind, consents, soft issues, document source and confidence."""
from __future__ import annotations

from formguide.attachments import extract as att

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value


def card(guide, model, thread, changes, state=None, caps=None, before=()):
    model.script = [*before, say("", ("c1", "propose_changes", {"changes": changes}))]
    state = state or start(guide, LOAN)
    ev = collect(guide, thread, message="fill it", state=state, capabilities=caps)
    return interrupt_value(ev)


def test_every_change_has_its_kind(guide, model):
    v = card(guide, model, "k1", [{"name": "passport_number", "value": "123456"},
                                  {"name": "birth_date", "value": "1990-03-12"}])
    assert [c["kind"] for c in v["changes"]] == ["text", "date"]


def test_consent_rows_from_the_pack(guide, model):
    state = start(guide, LOAN)
    guide.packs.get("loan_application").consents["contact_messenger"] = {
        "required": False, "doc": {"title": "Messaging terms", "text": "We may write to you."}}
    v = card(guide, model, "k2", [{"name": "contact_messenger", "value": True}], state=state)
    row = v["changes"][0]
    assert row["consent"] is True and row["required"] is False and row["doc"]["title"] == "Messaging terms"
    v = card(guide, model, "k3", [{"name": "contact_messenger", "value": True}], state=state, caps=["ask"])
    assert "consent" not in v["changes"][0]                       # the client cannot show consent rows


def test_soft_issue_on_a_row(guide, model):
    v = card(guide, model, "k4", [{"name": "dependents_count", "value": 9, "issue": "Unusually many dependants."}])
    assert v["changes"][0]["issue"] == {"severity": "warning", "message": "Unusually many dependants."}
    v = card(guide, model, "k5", [{"name": "dependents_count", "value": 9, "issue": "x"}], caps=["ask"])
    assert "issue" not in v["changes"][0]


def test_values_from_a_document_carry_source_and_confidence(guide, model, monkeypatch):
    async def fake(model_, ov, filename, data, names):
        return att.Extraction(document_type="Passport", notes="", fields=[
            att.ExtractedField(field="last_name", value="Smith", confidence="high", evidence="page 2"),
            att.ExtractedField(field="passport_issued_by", value="Kazan office", confidence="low", evidence="blurred")])
    monkeypatch.setattr(att, "extract", fake)
    a = guide.attachments.save("k6", "passport.jpg", b"\xff\xd8 fake")
    read = say("", ("x1", "extract_from_attachment", {"attachment_id": a["id"]}))
    v = card(guide, model, "k6", [{"name": "last_name", "value": "Smith"},
                                  {"name": "passport_issued_by", "value": "Kazan office"},
                                  {"name": "first_name", "value": "Anna"}], before=[read])
    assert v["source"] == {"kind": "document", "title": "Passport", "attachment_id": a["id"], "found": 2}
    assert [c.get("confidence") for c in v["changes"]] == ["high", "low", None]
    entry = guide.thread("k6")["pending_card"]
    assert entry["source"]["title"] == "Passport"                  # restored with the card after a reload
