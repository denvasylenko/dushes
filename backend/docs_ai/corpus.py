"""The documentation corpus: the site's llms-full.txt split into pages and sections, searched with BM25.

llms-full.txt is every page as Markdown, each headed by `<!-- page: <url> -->` and separated by `---`.
A section is a page's text under one `##` heading; its address is the page URL plus the heading's anchor.
"""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from formguide import BM25Index, Chunk

NS = "docs"
SPEC_WEIGHT = 0.6   # behaviour contracts answer "what must happen", guides answer "how do I"
_MERMAID = re.compile(r"```mermaid\n[\s\S]*?```\n?")
_PAGE = re.compile(r"^<!-- page: (\S+) -->\n", re.M)


def slug(heading: str) -> str:
    """The anchor Starlight (github-slugger) gives a heading."""
    s = re.sub(r"[`*_\[\]()<>]", "", heading.strip().lower())
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


@dataclass
class Corpus:
    index: BM25Index
    pages: int
    sections: int
    source: str

    def search(self, query: str, k: int = 6) -> list[Chunk]:
        """Guides first: a spec passage counts for less than a guide passage with the same score."""
        hits = [(s * (SPEC_WEIGHT if "/specifications/" in c.doc_id else 1.0), c) for s, c in self.index.search([NS], query, k * 3)]
        return [c for _, c in sorted(hits, key=lambda x: -x[0])[:k]]


def split(text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    marks = list(_PAGE.finditer(text))
    for i, m in enumerate(marks):
        url = m.group(1)
        body = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        body = _MERMAID.sub("", re.sub(r"\n---\s*$", "", body.strip()))   # diagrams are noise for retrieval
        title = (re.search(r"^# (.+)$", body, re.M) or [None, url])[1]
        parts = re.split(r"(?m)^## ", body)
        for n, part in enumerate(parts):
            head, _, rest = part.partition("\n") if n else ("", "", part)
            section = head.strip() if n else title
            anchor = f"#{slug(head)}" if n else ""
            content = (rest if n else part).strip()
            if len(content) < 20:
                continue
            for j, piece in enumerate(_pieces(content)):
                chunks.append(Chunk(id=f"{url}{anchor}~{j}", namespace=NS, doc_id=url + anchor, title=str(title),
                                    section=section, text=piece))
    return chunks


def _pieces(text: str, size: int = 2400) -> list[str]:
    """Long sections in pieces of about `size` characters, cut at blank lines (never inside a code block)."""
    out, cur, in_code = [], "", False
    for block in text.split("\n\n"):
        if block.count("```") % 2:
            in_code = not in_code
        if len(cur) + len(block) > size and cur and not in_code:
            out.append(cur.strip())
            cur = ""
        cur += block + "\n\n"
    if cur.strip():
        out.append(cur.strip())
    return out


def read(source: str, timeout: float = 20) -> str:
    """A URL (https://.../llms-full.txt) or a local path."""
    if re.match(r"https?://", source):
        req = urllib.request.Request(source, headers={"User-Agent": "formguide-docs-ai"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — the configured docs URL
            return r.read().decode("utf-8")
    return Path(source).read_text(encoding="utf-8")


def load(source: str) -> Corpus:
    chunks = split(read(source))
    if not chunks:
        raise ValueError(f"no pages in {source}: expected llms-full.txt with <!-- page: ... --> markers")
    idx = BM25Index()
    idx.add(chunks)
    return Corpus(index=idx, pages=len({c.doc_id.split('#')[0] for c in chunks}), sections=len(chunks), source=source)
