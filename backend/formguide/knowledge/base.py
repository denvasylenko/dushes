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
from typing import Any

from .index import BM25Index, Chunk, SearchIndex
from .store import CHUNK_CHARS, CHUNK_OVERLAP, DocumentStore

PER_DOCUMENT = 4     # of 6 results, at most this many from one document while another has comparable hits
COMPARABLE = 0.5     # "comparable": at least this share of the top score


class KnowledgeBase:
    def __init__(self, root: str | Path, index: SearchIndex | None = None,
                 scopes: dict[str, list[str]] | None = None, chunk_chars: int = CHUNK_CHARS,
                 chunk_overlap: int = CHUNK_OVERLAP, document_url: str = ""):
        # the host's link to a document, for the sources a person taps: "https://host/docs/{filename}#page={page}"
        # ({filename}, {doc_id}, {namespace}, {page}); empty: a source shows its passage and no link
        self.document_url = document_url
        self.store = DocumentStore(root, chunk_chars, chunk_overlap)
        self.index: SearchIndex = index or BM25Index()
        # with a vector index the words are searched too: an exact figure or a clause number is lexical
        self.lexical: BM25Index | None = None if isinstance(self.index, BM25Index) else BM25Index()
        self.scopes = dict(scopes or {})
        self._by_id: dict[str, dict[str, Chunk]] = {}     # namespace -> section id -> section
        for ns in self.store.namespaces():
            chunks = self.store.chunks(ns)                 # an older chunks.json is cut again here
            old = self.store.recut.pop(ns, None)
            if self.index.ephemeral:                       # rebuild an in-memory index from what is on disk
                self.index.add(chunks)
            elif old is not None:                          # a persistent index still holds the old sections
                self.index.delete(old)
                self.index.add(chunks)
            if self.lexical is not None:
                self.lexical.add(chunks)

    def _sections(self, namespace: str) -> dict[str, Chunk]:
        if namespace not in self._by_id:
            self._by_id[namespace] = {c.id: c for c in self.store.chunks(namespace)}
        return self._by_id[namespace]

    def namespaces_for(self, form_id: str) -> list[str]:
        return list(self.scopes.get(form_id) or [form_id])

    # ------------------------------------------------------------ documents
    def add_document(self, namespace: str, filename: str, data: bytes) -> dict:
        meta, chunks = self.store.add(namespace, filename, data)
        self.index.add(chunks)
        if self.lexical is not None:
            self.lexical.add(chunks)
        self._by_id.pop(namespace, None)
        return meta

    def delete_document(self, namespace: str, doc_id: str) -> bool:
        gone = self.store.delete(namespace, doc_id)
        self.index.delete(gone)
        if self.lexical is not None:
            self.lexical.delete(gone)
        self._by_id.pop(namespace, None)
        return bool(gone) or any(d["doc_id"] == doc_id for d in self.store.list(namespace))

    def list_documents(self, namespace: str) -> list[dict]:
        return self.store.list(namespace)

    def documents_for(self, form_id: str) -> list[dict]:
        return [d for ns in self.namespaces_for(form_id) for d in self.store.list(ns)]

    # ------------------------------------------------------------ retrieval
    def search(self, form_id: str, query: str, k: int = 6, per_document: int | None = None) -> list[tuple[float, Chunk]]:
        """The best sections for a query across the form's documents. The words are always searched; a
        configured vector index is fused with them (reciprocal ranks). No more than `per_document` results come
        from one document while another document has hits of comparable score."""
        spaces = self.namespaces_for(form_id)
        wide = max(k * 4, 24)
        hits = self.index.search(spaces, query, wide)
        if self.lexical is not None:
            hits = _fuse(hits, self.lexical.search(spaces, query, wide))
        return _spread(hits, k, per_document if per_document is not None else max(2, round(k * PER_DOCUMENT / 6)))

    def section(self, form_id: str, chunk_id: str) -> Chunk | None:
        for ns in self.namespaces_for(form_id):
            c = self._sections(ns).get(chunk_id)
            if c:
                return c
        return None

    def neighbours(self, form_id: str, chunk_id: str, before: int = 1, after: int = 1) -> list[Chunk]:
        """The sections around one, in the document's order (the section itself included)."""
        c = self.section(form_id, chunk_id)
        if c is None:
            return []
        doc = sorted((x for x in self._sections(c.namespace).values() if x.doc_id == c.doc_id), key=lambda x: x.order)
        i = next(n for n, x in enumerate(doc) if x.id == c.id)
        return doc[max(0, i - before): i + after + 1]

    def outline(self, form_id: str) -> list[dict[str, Any]]:
        """Each document in scope as its headings: [{doc_id, namespace, title, chars, pages, headings:
        [{path, page, chars, sections}]}]. Built from the sections, no model call."""
        out = []
        for ns in self.namespaces_for(form_id):
            names = {d["doc_id"]: d["filename"] for d in self.store.list(ns)}
            docs: dict[str, list[Chunk]] = {}
            for c in self._sections(ns).values():
                docs.setdefault(c.doc_id, []).append(c)
            for doc_id, chunks in docs.items():
                chunks.sort(key=lambda x: x.order)
                heads: dict[str, dict[str, Any]] = {}
                for c in chunks:
                    h = heads.setdefault(c.path or c.section, {"path": c.path or c.section, "page": c.page,
                                                               "chars": 0, "sections": 0})
                    h["chars"] += len(c.text)
                    h["sections"] += 1
                pages = [c.page for c in chunks if c.page]
                out.append({"doc_id": doc_id, "namespace": ns, "title": names.get(doc_id) or chunks[0].title,
                            "chars": sum(len(c.text) for c in chunks), "pages": max(pages) if pages else None,
                            "headings": list(heads.values())})
        return out

    def all_text(self, form_id: str) -> str:
        return self.store.all_text(self.namespaces_for(form_id))

    # ------------------------------------------------------------ compiled
    def compiled(self, form_id: str) -> dict | None:
        return self.store.load_compiled(form_id)

    def save_compiled(self, form_id: str, data: dict) -> None:
        self.store.save_compiled(form_id, data)


def _fuse(a: list[tuple[float, Chunk]], b: list[tuple[float, Chunk]]) -> list[tuple[float, Chunk]]:
    """Two rankings as one, by reciprocal rank (their scores are not comparable)."""
    score: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for hits in (a, b):
        for rank, (_s, c) in enumerate(hits):
            score[c.id] = score.get(c.id, 0.0) + 1.0 / (60 + rank)
            by_id.setdefault(c.id, c)
    return sorted(((s, by_id[i]) for i, s in score.items()), key=lambda x: (-x[0], x[1].id))


def _spread(hits: list[tuple[float, Chunk]], k: int, per_document: int) -> list[tuple[float, Chunk]]:
    """The top `k`, but not all from one document while another has hits of comparable score."""
    if not hits:
        return []
    bar = hits[0][0] * COMPARABLE
    docs = {(c.namespace, c.doc_id) for s, c in hits if s >= bar}
    if len(docs) < 2:
        return hits[:k]
    taken: dict[tuple[str, str], int] = {}
    out, rest = [], []
    for s, c in hits:
        key = (c.namespace, c.doc_id)
        if taken.get(key, 0) < per_document:
            taken[key] = taken.get(key, 0) + 1
            out.append((s, c))
        else:
            rest.append((s, c))
        if len(out) == k:
            return out
    return (out + rest)[:k]
