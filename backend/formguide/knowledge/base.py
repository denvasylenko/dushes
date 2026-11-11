"""KnowledgeBase: business documents uploaded by managers, scoped to forms.

    KnowledgeBase(
        root="data/kb",
        index=VectorStoreIndex(PGVector(...), filter_builder=lambda ns: {"namespace": {"$in": ns}}),
        scopes={"loan_application": ["loan_application", "bank_common"]},
    )

- Documents are uploaded into a namespace (by default the form id).
- `scopes` says which namespaces each form sees; a form not listed sees its own namespace.
- Compiled knowledge (rules, field notes) is stored per form and merged into its domain pack.
"""
from __future__ import annotations

from pathlib import Path

from .index import BM25Index, Chunk, SearchIndex
from .store import DocumentStore


class KnowledgeBase:
    def __init__(self, root: str | Path, index: SearchIndex | None = None,
                 scopes: dict[str, list[str]] | None = None):
        self.store = DocumentStore(root)
        self.index: SearchIndex = index or BM25Index()
        self.scopes = dict(scopes or {})
        if self.index.ephemeral:   # rebuild an in-memory index from what is on disk
            for ns in self.store.namespaces():
                self.index.add(self.store.chunks(ns))

    def namespaces_for(self, form_id: str) -> list[str]:
        return list(self.scopes.get(form_id) or [form_id])

    # ------------------------------------------------------------ documents
    def add_document(self, namespace: str, filename: str, data: bytes) -> dict:
        meta, chunks = self.store.add(namespace, filename, data)
        self.index.add(chunks)
        return meta

    def delete_document(self, namespace: str, doc_id: str) -> bool:
        gone = self.store.delete(namespace, doc_id)
        self.index.delete(gone)
        return bool(gone) or any(d["doc_id"] == doc_id for d in self.store.list(namespace))

    def list_documents(self, namespace: str) -> list[dict]:
        return self.store.list(namespace)

    def documents_for(self, form_id: str) -> list[dict]:
        return [d for ns in self.namespaces_for(form_id) for d in self.store.list(ns)]

    # ------------------------------------------------------------ retrieval
    def search(self, form_id: str, query: str, k: int = 6) -> list[tuple[float, Chunk]]:
        return self.index.search(self.namespaces_for(form_id), query, k)

    def section(self, form_id: str, chunk_id: str) -> Chunk | None:
        for ns in self.namespaces_for(form_id):
            for c in self.store.chunks(ns):
                if c.id == chunk_id:
                    return c
        return None

    def all_text(self, form_id: str) -> str:
        return self.store.all_text(self.namespaces_for(form_id))

    # ------------------------------------------------------------ compiled
    def compiled(self, form_id: str) -> dict | None:
        return self.store.load_compiled(form_id)

    def save_compiled(self, form_id: str, data: dict) -> None:
        self.store.save_compiled(form_id, data)
