"""Configuration and providers, offline: YAML loading, OpenAI/Azure/Anthropic request payloads,
vector-store index with namespaces and scopes, domain-pack sources, attachments."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage

from demo.mock_forms import FORMS
from formguide import AttachmentStore, DomainPackRegistry, FormGuide, KnowledgeBase, VectorStoreIndex, load_config
from formguide.agent.tools import tool_schemas
from formguide.form.layout import LayoutIndex
from formguide.form.overlay import Overlay
from formguide.models import build_model, file_block, provider_of, system_message
from formguide.attachments import extract as att

from .conftest import DEMO, SAMPLES


class HashEmbeddings(Embeddings):
    """Bag-of-words hashed into 64 dims: enough to test the adapter without a provider."""

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * 64
        for w in text.lower().split():
            v[hash(w) % 64] += 1.0
        return v

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class MiniVectorStore:
    """The three methods VectorStoreIndex uses from a LangChain VectorStore (cosine over HashEmbeddings)."""

    def __init__(self, emb: Embeddings):
        self.emb, self.rows = emb, {}

    def add_documents(self, docs, ids):
        for d, i, v in zip(docs, ids, self.emb.embed_documents([d.page_content for d in docs])):
            self.rows[i] = (d, v)

    def delete(self, ids):
        for i in ids:
            self.rows.pop(i, None)

    def similarity_search_with_score(self, query, k=4, filter=None):
        q = self.emb.embed_query(query)

        def cos(v):
            n = (sum(x * x for x in q) * sum(x * x for x in v)) ** 0.5
            return sum(a * b for a, b in zip(q, v)) / n if n else 0.0
        rows = sorted(((d, cos(v)) for d, v in self.rows.values()), key=lambda x: -x[1])
        return rows[:k]


@pytest.fixture(autouse=True)
def fake_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", "test"))
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("OPENAI_API_VERSION", "2025-04-01-preview")


def test_demo_yaml_loads(tmp_path):
    cfg = load_config(DEMO / "formguide.yaml")
    cfg.data_dir = tmp_path
    cfg.knowledge = KnowledgeBase(tmp_path / "kb", scopes=cfg.knowledge.scopes)
    g = FormGuide(cfg)
    assert provider_of(g.models.agent) == "anthropic" and provider_of(g.models.research) == "anthropic"
    assert g.knowledge.namespaces_for("loan_application") == ["loan_application", "bank_common"]
    assert [s.name for s in g.skills.for_form("barber_booking")] == ["gift_cards"]


def test_yaml_with_azure_and_openai(tmp_path):
    y = tmp_path / "g.yaml"
    y.write_text("""
data_dir: data
models:
  agent: {class: "langchain_openai:AzureChatOpenAI", azure_deployment: gpt-5, api_version: "2025-04-01-preview",
          azure_endpoint: "${AZURE_OPENAI_ENDPOINT}"}
  research: "openai:gpt-5-mini"
components: {containers: {Wizard: tabs, Step: tab}, fields: {TextField: text}}
tools: ["demo.skill_tools:check_gift_card"]
""")
    g = FormGuide(load_config(y))
    assert type(g.models.agent).__name__ == "AzureChatOpenAI" and g.models.agent.azure_endpoint.startswith("https://")
    assert type(g.models.research).__name__ == "ChatOpenAI"
    assert g.models.extract is g.models.agent                    # unset roles fall back to the agent model
    assert g.register_form('<Wizard name="w"><Step name="s"><TextField name="a" /></Step></Wizard>')["warnings"] == []
    assert [t.name for t in g.tools_for("any")] == ["check_gift_card"]


def _payload(model, tools, messages):
    return model.bind_tools(tools)._get_request_payload(messages) if hasattr(model, "_get_request_payload") \
        else None


@pytest.mark.parametrize("spec", [
    {"class": "langchain_openai:ChatOpenAI", "model": "gpt-5"},
    {"class": "langchain_openai:AzureChatOpenAI", "azure_deployment": "gpt-5", "api_version": "2025-04-01-preview"},
    {"provider": "anthropic", "model": "claude-opus-5-5"},
])
def test_providers_accept_our_tools_and_files(spec):
    """Build the real request payload (no network): our tools + an image + a PDF + system prompt."""
    m = build_model(spec)
    png = (SAMPLES / "attachments" / "business_card.png").read_bytes()
    msgs = [system_message("You help.", m), HumanMessage(content=[
        file_block("card.png", "image/png", png), file_block("a.pdf", "application/pdf", b"%PDF-1.4 fake"),
        file_block("n.txt", "text/plain", "Name: Sam".encode()), {"type": "text", "text": "hi"}])]
    bound = m.bind_tools(tool_schemas([]))
    payload = m._get_request_payload(msgs, **bound.kwargs)
    tool_names = {(t.get("function") or t).get("name") for t in payload["tools"]}
    assert {"propose_changes", "focus_field", "use_skill"} <= tool_names
    flat = str(payload)
    assert "image" in flat and ("application/pdf" in flat or "file" in flat)


def test_vector_store_index_with_scopes(tmp_path):
    vs = MiniVectorStore(HashEmbeddings())
    kb = KnowledgeBase(tmp_path / "kb", index=VectorStoreIndex(vs),
                       scopes={"loan_application": ["loan_application", "bank_common"]})
    kb.add_document("loan_application", "tariffs.md", (SAMPLES / "kb/loan_application/tariffs_2026.md").read_bytes())
    kb.add_document("bank_common", "hours.md", b"# Hours\n\nBranches are open 9-18 on weekdays.")
    kb.add_document("barber_booking", "policies.md", (SAMPLES / "kb/barber_booking/salon_policies.md").read_bytes())
    hits = kb.search("loan_application", "branch hours", k=20)
    assert {c.namespace for _s, c in hits} <= {"loan_application", "bank_common"}
    assert any(c.namespace == "bank_common" for _s, c in hits)              # shared namespace is in scope
    assert all(c.namespace == "barber_booking" for _s, c in kb.search("barber_booking", "anything", k=20))
    doc = kb.list_documents("bank_common")[0]["doc_id"]
    assert kb.delete_document("bank_common", doc)
    assert not any(c.namespace == "bank_common" for _s, c in kb.search("loan_application", "hours", k=20))


def test_domain_pack_sources_and_knowledge_merge(tmp_path):
    reg = DomainPackRegistry(directory=DEMO / "domain_packs", packs={"x": {"title": "X form"}},
                             provider=lambda fid: {"title": "From DB"} if fid == "db_form" else None)
    reg.knowledge = KnowledgeBase(tmp_path / "kb")
    assert reg.get("loan_application").source == "dir"
    assert reg.get("x").title == "X form" and reg.get("db_form").source == "provider"
    assert reg.get("dentist").source == "default" and reg.get("dentist").title == "Dentist"
    reg.register("x", {"title": "Inline X"})
    assert reg.get("x").source == "inline"
    reg.knowledge.add_document("x", "rules.md", b"# Rules\n\nNo pets.")
    reg.knowledge.save_compiled("x", {"rules": ["No pets (rules.md)"], "field_notes": {}})
    p = reg.get("x")
    assert p.source == "inline+kb" and p.rules == ["No pets (rules.md)"] and p.kb_documents == ["rules.md"]


def test_attachment_store_and_catalog(tmp_path):
    store = AttachmentStore(tmp_path)
    meta = store.save("thread-1", "card.png", (SAMPLES / "attachments" / "business_card.png").read_bytes())
    assert store.load("thread-1", meta["id"])[0] == "card.png"
    assert store.load("thread-2", meta["id"]) is None and store.load("thread-1", "../../etc") is None
    with pytest.raises(ValueError):
        store.save("thread-1", "evil.exe", b"MZ")
    f = FORMS["barber_booking"]
    ov = Overlay(LayoutIndex(f.jsx), f.compute(None))
    names = att.candidate_fields(ov, None, "step_contacts")
    assert "client_phone" in names and "summary" not in names
    x = att.Extraction(document_type="card", notes="", fields=[
        att.ExtractedField(field="client_phone", value="+1 555", confidence="high", evidence="front")])
    assert "disabled now (fill later)" in att.describe(ov, "card.png", x)


def test_kb_bm25_scoped(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb")
    for p in sorted((SAMPLES / "kb" / "loan_application").iterdir()):
        kb.add_document("loan_application", p.name, p.read_bytes())
    hits = kb.search("loan_application", "sole proprietors registered tax return")
    assert any("tax return" in c.text for _s, c in hits)
    assert kb.search("barber_booking", "loan") == []
    kb2 = KnowledgeBase(tmp_path / "kb")                                     # in-memory BM25 rebuilt from disk
    assert kb2.search("loan_application", "tax return")
    with pytest.raises(ValueError):
        kb.add_document("../etc", "a.md", b"x")


def test_yaml_model_shorthands(tmp_path, monkeypatch):
    from formguide import load_config
    from formguide.config import GuideConfig

    f = tmp_path / "a.yaml"
    f.write_text('model: "openai:gpt-5"\n')
    m = load_config(f).models
    assert m.agent == "openai:gpt-5" and m.research is None            # other roles fall back to agent
    f.write_text('model: "openai:gpt-5"\nmodels: {agent: "anthropic:claude-opus-5-5", extract: "openai:gpt-5"}\n')
    m = load_config(f).models
    assert m.agent == "anthropic:claude-opus-5-5" and m.extract == "openai:gpt-5"   # models wins
    f.write_text('models: "openai:gpt-5-mini"\ndata_dir: ${FG_TEST_DIR}\n')
    monkeypatch.setenv("FG_TEST_DIR", "store")
    cfg = load_config(f)
    assert cfg.models.agent == "openai:gpt-5-mini" and cfg.data_dir == (tmp_path / "store").resolve()
    monkeypatch.setenv("FORMGUIDE_MODEL", "openai:gpt-5")
    assert GuideConfig().models.agent == "openai:gpt-5"
