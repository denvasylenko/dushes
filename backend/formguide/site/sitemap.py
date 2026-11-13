"""The site map: a site's pages, their tabs, accordions and sections, and which form each page holds.

It is both what the site assistant knows (a BM25 index over every section) and where it may go:
navigation targets are checked against it, so the model cannot invent pages.

    title: Main Street
    pages:
      - path: /loans
        title: Loans
        description: ...
        keywords: [rate, interest]          # optional: words that point to this page from another one
        form: loan_application              # optional: the form on this page
        tabs:       [{id: car, title: Car loan, text: ...}]
        accordions: [{id: early, title: Can I repay early?, text: ...}]
        sections:   [{id: documents, title: Documents you need, text: ...}]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..knowledge.index import BM25Index, Chunk

NS = "site"
KINDS = ("tabs", "accordions", "sections")


@dataclass
class Part:
    """A tab, an accordion or a section of a page."""
    kind: str     # tab | accordion | section
    id: str
    title: str
    text: str


@dataclass
class Page:
    path: str
    title: str
    description: str = ""
    form: str | None = None
    keywords: list[str] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)

    def part(self, pid: str) -> Part | None:
        return next((p for p in self.parts if p.id == pid), None)


class SiteMap:
    def __init__(self, title: str, pages: list[Page]):
        self.title = title
        self.pages = pages
        self.by_path = {p.path: p for p in pages}
        self.index = BM25Index()
        self.index.add([Chunk(f"{p.path}#{x.id}", NS, p.path, p.title, x.title, x.text) for p in pages for x in p.parts]
                       + [Chunk(f"{p.path}#", NS, p.path, p.title, p.title, f"{p.description} {' '.join(p.keywords)}")
                          for p in pages if p.description or p.keywords])

    @classmethod
    def load(cls, source: str | Path | dict) -> SiteMap:
        raw = source if isinstance(source, dict) else yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        pages = []
        for p in raw.get("pages") or []:
            parts = [Part(kind[:-1] if kind != "accordions" else "accordion", str(x["id"]), str(x.get("title") or x["id"]),
                          str(x.get("text") or "")) for kind in KINDS for x in p.get(kind) or []]
            pages.append(Page(path=str(p["path"]), title=str(p.get("title") or p["path"]),
                              description=str(p.get("description") or ""), form=p.get("form"),
                              keywords=[str(k).lower() for k in p.get("keywords") or []], parts=parts))
        if not pages:
            raise ValueError("the site map has no pages")
        return cls(str(raw.get("title") or "Site"), pages)

    # ------------------------------------------------------------ lookups
    def page(self, path: str) -> Page | None:
        return self.by_path.get(path) or self.by_path.get(path.rstrip("/") or "/")

    def form_page(self, form_id: str) -> Page | None:
        return next((p for p in self.pages if p.form == form_id), None)

    def search(self, query: str, k: int = 5) -> list[Chunk]:
        return [c for _s, c in self.index.search([NS], query, k)]

    def contents(self) -> str:
        """One line per page for the model: path, title, what is on it."""
        out = []
        for p in self.pages:
            parts = ", ".join(f"{x.kind} {x.id} ({x.title})" for x in p.parts)
            form = f" | form: {p.form}" if p.form else ""
            out.append(f"{p.path} | {p.title} | {p.description}{form}" + (f" | {parts}" if parts else ""))
        return "\n".join(out)

    def as_dict(self) -> dict[str, Any]:
        """For the page: what to render."""
        return {"title": self.title, "pages": [
            {"path": p.path, "title": p.title, "description": p.description, "form": p.form,
             **{k: [{"id": x.id, "title": x.title, "text": x.text} for x in p.parts if x.kind == k[:-1] or
                    (k == "accordions" and x.kind == "accordion")] for k in KINDS}} for p in self.pages]}
