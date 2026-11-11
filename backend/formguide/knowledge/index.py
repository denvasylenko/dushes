"""Search indexes over document sections. Pick one in the config:

- BM25Index:        built in, no dependencies, lexical (any language, crude stemming).
- VectorStoreIndex: wraps any LangChain VectorStore (Chroma, PGVector, Qdrant, Azure AI
                    Search, Pinecone, InMemoryVectorStore...) with its embeddings.

Sections are tagged with a `namespace`; a form searches the namespaces in its
scope (see KnowledgeBase.scopes), so documents can be per form or shared.
"""
from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Protocol

_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass
class Chunk:
    id: str          # "<doc_id>#<n>"
    namespace: str   # where the document was uploaded (a form id or a shared space)
    doc_id: str
    title: str       # document title (file name)
    section: str     # nearest heading
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stems(text: str) -> list[str]:
    # normalize Cyrillic yo to ye so both spellings match
    words = _WORD.findall(text.lower().replace("\u0451", "\u0435").replace("_", " "))
    return [w[:5] if len(w) > 5 else w for w in words if len(w) > 1]


class SearchIndex(Protocol):
    #: True if the index lives in memory and must be rebuilt from stored chunks on start.
    ephemeral: bool

    def add(self, chunks: list[Chunk]) -> None: ...
    def delete(self, chunks: list[Chunk]) -> None: ...
    def search(self, namespaces: list[str], query: str, k: int) -> list[tuple[float, Chunk]]: ...


class BM25Index:
    ephemeral = True

    def __init__(self) -> None:
        self._by_ns: dict[str, dict[str, Chunk]] = {}

    def add(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._by_ns.setdefault(c.namespace, {})[c.id] = c

    def delete(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._by_ns.get(c.namespace, {}).pop(c.id, None)

    def search(self, namespaces: list[str], query: str, k: int = 6) -> list[tuple[float, Chunk]]:
        chunks = [c for ns in namespaces for c in self._by_ns.get(ns, {}).values()]
        q = set(stems(query))
        if not chunks or not q:
            return []
        docs = [stems(f"{c.section} {c.text}") for c in chunks]
        avg = sum(map(len, docs)) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        scored = []
        for c, d in zip(chunks, docs):
            tf = Counter(d)
            s = 0.0
            for t in q:
                if t in tf:
                    idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                    s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / avg))
            if s > 0:
                scored.append((s, c))
        scored.sort(key=lambda x: -x[0])
        return scored[:k]


class VectorStoreIndex:
    """Adapter for any LangChain VectorStore.

    filter_builder(namespaces) -> the store's native metadata filter, e.g.
      Chroma:   lambda ns: {"namespace": {"$in": ns}}
      PGVector: lambda ns: {"namespace": {"$in": ns}}
    Without it, results are over-fetched (k * fetch_factor) and filtered in Python,
    which works with any store.
    """
    ephemeral = False

    def __init__(self, vectorstore: Any, filter_builder: Callable[[list[str]], Any] | None = None,
                 fetch_factor: int = 5):
        self.vs = vectorstore
        self.filter_builder = filter_builder
        self.fetch_factor = fetch_factor

    @staticmethod
    def _vid(c: Chunk) -> str:
        # Many stores require UUID ids; derive a stable one.
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"formguide:{c.namespace}:{c.id}"))

    def add(self, chunks: list[Chunk]) -> None:
        from langchain_core.documents import Document

        if not chunks:
            return
        docs = [Document(page_content=f"{c.section}\n{c.text}", metadata=c.to_dict()) for c in chunks]
        self.vs.add_documents(docs, ids=[self._vid(c) for c in chunks])

    def delete(self, chunks: list[Chunk]) -> None:
        if chunks:
            self.vs.delete(ids=[self._vid(c) for c in chunks])

    def search(self, namespaces: list[str], query: str, k: int = 6) -> list[tuple[float, Chunk]]:
        wanted = set(namespaces)
        if self.filter_builder:
            hits = self.vs.similarity_search_with_score(query, k=k, filter=self.filter_builder(namespaces))
        else:
            hits = self.vs.similarity_search_with_score(query, k=k * self.fetch_factor)
        out = []
        for doc, score in hits:
            m = doc.metadata or {}
            if m.get("namespace") not in wanted:
                continue
            out.append((float(score), Chunk(**{f: m.get(f, "") for f in Chunk.__dataclass_fields__})))
        return out[:k]
