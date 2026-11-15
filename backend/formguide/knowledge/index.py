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
# figures and clause numbers as written ("4.2", "27,90", "2026-11-15"), and codes with digits in them ("DE89", "A-118")
_FIGURE = re.compile(r"\d+(?:[.,:/\-]\d+)+|\b[^\W\d_]+[\-]?\d[\w\-]*|\b\d[\w\-]*[^\W\d_][\w\-]*", re.UNICODE)

# words of a question that say nothing about its subject (a few per language; non-ASCII letters as escapes)
STOP = frozenset("""
a an the of to in on at for by with from and or but not is are was were be been do does did can could may must
shall should will would have has had i me my we us our you your he she it its they them their this that these those
what which who whom when where why how many much long often there here any some all each per as if so than then
please tell know need want get give show find about into over under up out
der die das den dem des ein eine einen einem einer und oder ist sind was wie wer wo wann warum welche welcher
ich wir mein unser sie ihr es zu von mit auf bei nach aus pro
el la los las un una y o es son que como cuando donde cual cuanto mi nuestro de del en con por para
le les une et ou est sont que qui quoi comment quand quel quelle mon notre des du dans avec pour par
il lo gli i uno e che come quando dove quale quanto mio nostro di del della con per
""".split()) | frozenset(("\u0438", "\u0432", "\u043d\u0430", "\u043a\u0430\u043a", "\u0447\u0442\u043e",
                              "\u044d\u0442\u043e", "\u043f\u043e", "\u0434\u043b\u044f", "\u0443", "\u0437\u0430",
                              "\u0456", "\u0442\u0430", "\u044f\u043a", "\u0449\u043e"))

W_PATH = 1.5     # a match in a section's heading path, next to a match in its text
W_TITLE = 0.5    # a match in the document's title


@dataclass
class Chunk:
    id: str          # "<doc_id>#<n>"
    namespace: str   # where the document was uploaded (a form id or a shared space)
    doc_id: str
    title: str       # document title (file name)
    section: str     # nearest heading
    text: str
    path: str = ""           # the heading chain, "4 Fees > 4.2 Late payment"; "" for sections cut before paths existed
    page: int | None = None  # the PDF page the section starts on
    order: int = 0           # its place in the document

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stems(text: str) -> list[str]:
    # normalize Cyrillic yo to ye so both spellings match
    low = text.lower().replace("\u0451", "\u0435")
    words = _WORD.findall(low.replace("_", " "))
    out = [w[:5] if len(w) > 5 else w for w in words if len(w) > 1]
    for f in _FIGURE.findall(low):   # also whole, so an exact figure or clause number is findable as written
        out.append(f)
        if "," in f:
            out.append(f.replace(",", "."))
    return out


class SearchIndex(Protocol):
    #: True if the index lives in memory and must be rebuilt from stored chunks on start.
    ephemeral: bool

    def add(self, chunks: list[Chunk]) -> None: ...
    def delete(self, chunks: list[Chunk]) -> None: ...
    def search(self, namespaces: list[str], query: str, k: int) -> list[tuple[float, Chunk]]: ...


class _Postings:
    """One namespace's sections: term -> {section id: count}, for the text and for the heading path."""

    def __init__(self) -> None:
        self.chunks: dict[str, Chunk] = {}
        self.text: dict[str, dict[str, int]] = {}
        self.path: dict[str, dict[str, int]] = {}
        self.title: dict[str, set[str]] = {}       # section id -> the stems of its document's title
        self.len_text: dict[str, int] = {}
        self.len_path: dict[str, int] = {}
        self.sum_text = 0
        self.sum_path = 0

    def add(self, c: Chunk) -> None:
        if c.id in self.chunks:
            self.remove(c.id)
        self.chunks[c.id] = c
        # a section without a heading path is indexed as before paths existed: its heading with its text
        body = Counter(stems(c.text if c.path else f"{c.section} {c.text}"))
        # the document's name stands at the top of every path, whether the file had a title line of its own or not
        # (a PDF has none): a question that names a document finds that document's sections
        name = re.sub(r"\.(md|txt|pdf)$", "", c.title, flags=re.IGNORECASE)
        head = Counter(stems(f"{name} {c.path}")) if c.path else Counter()
        for t, n in body.items():
            self.text.setdefault(t, {})[c.id] = n
        for t, n in head.items():
            self.path.setdefault(t, {})[c.id] = n
        self.len_text[c.id], self.len_path[c.id] = sum(body.values()), sum(head.values())
        self.sum_text += self.len_text[c.id]
        self.sum_path += self.len_path[c.id]
        if c.path:
            self.title[c.id] = set(stems(c.title))

    def remove(self, cid: str) -> None:
        if self.chunks.pop(cid, None) is None:
            return
        for table in (self.text, self.path):
            for t in [t for t, ids in table.items() if cid in ids]:
                del table[t][cid]
                if not table[t]:
                    del table[t]
        self.sum_text -= self.len_text.pop(cid, 0)
        self.sum_path -= self.len_path.pop(cid, 0)
        self.title.pop(cid, None)


class BM25Index:
    """Lexical search over prebuilt postings: a query reads only the entries of its own terms."""
    ephemeral = True

    def __init__(self) -> None:
        self._by_ns: dict[str, _Postings] = {}

    def add(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._by_ns.setdefault(c.namespace, _Postings()).add(c)

    def delete(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            if c.namespace in self._by_ns:
                self._by_ns[c.namespace].remove(c.id)

    def chunks(self, namespace: str) -> list[Chunk]:
        """Every section of a namespace."""
        p = self._by_ns.get(namespace)
        return list(p.chunks.values()) if p else []

    def search(self, namespaces: list[str], query: str, k: int = 6) -> list[tuple[float, Chunk]]:
        spaces = [self._by_ns[ns] for ns in dict.fromkeys(namespaces) if ns in self._by_ns]
        words = [w for w in _WORD.findall(query.lower()) if w not in STOP]
        q = set(stems(" ".join(words) if words else query))   # a question made only of small words is searched as it is
        q |= {f for f in stems(query) if any(ch.isdigit() for ch in f)}   # figures and codes are kept whatever they sit in
        n = sum(len(p.chunks) for p in spaces)
        if not n or not q:
            return []
        avg_text = sum(p.sum_text for p in spaces) / n or 1.0
        with_path = sum(1 for p in spaces for v in p.len_path.values() if v) or 1
        avg_path = sum(p.sum_path for p in spaces) / with_path or 1.0
        scores: dict[tuple[int, str], float] = {}
        for t in q:
            # a word's rarity is counted per field: a word that is in few headings marks the sections about it,
            # however common it is in running text (the small words of a question are dropped before this)
            for table, lens, avg, weight in (("text", "len_text", avg_text, 1.0), ("path", "len_path", avg_path, W_PATH)):
                df = sum(len(getattr(p, table).get(t, ())) for p in spaces)
                if not df:
                    continue
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                for i, p in enumerate(spaces):
                    size = getattr(p, lens)
                    for cid, tf in getattr(p, table).get(t, {}).items():
                        s = idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * size[cid] / avg))
                        scores[(i, cid)] = scores.get((i, cid), 0.0) + weight * s
        out = []
        for (i, cid), s in scores.items():
            title = spaces[i].title.get(cid)
            if title:
                s += W_TITLE * len(q & title) / len(q)
            out.append((s, spaces[i].chunks[cid]))
        out.sort(key=lambda x: (-x[0], x[1].id))
        return out[:k]


_TEXT_FIELDS = ("id", "namespace", "doc_id", "title", "section", "text", "path")


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
            out.append((float(score), Chunk(**{f: m[f] if f in m else ("" if f in _TEXT_FIELDS else None if f == "page" else 0)
                                               for f in Chunk.__dataclass_fields__})))
        return out[:k]
