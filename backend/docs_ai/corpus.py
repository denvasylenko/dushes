"""The documentation corpus: the site's llms-full.txt split into pages and sections, searched with BM25.

llms-full.txt is every page as Markdown, each headed by `<!-- page: <url> -->` and separated by `---`.
A section is a page's text under one `##` heading; its address is the page URL plus the heading's anchor.
"""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass, field
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
class Block:
    """One fenced code block of the docs."""
    id: str
    lang: str
    label: str      # the tab it sits in and / or its file title: "Anthropic \u00b7 formguide.yaml"
    code: str
    url: str        # the section's address
    page: str
    section: str


_FENCE = re.compile(r"^([ \t]*)```([\w+#.-]*)([^\n]*)\n(.*?)\n[ \t]*```[ \t]*$", re.M | re.S)
_TAB = re.compile(r"^\*\*([^*\n]{1,60})\*\*\s*$", re.M)


def mark_blocks(chunks: list[Chunk]) -> dict[str, Block]:
    """Give every code block an id and put a marker line `[code b12 \u00b7 yaml \u00b7 label]` before it, so the
    model can name the block and the server can quote it exactly."""
    blocks: dict[str, Block] = {}
    for c in chunks:
        out, pos = [], 0
        for m in _FENCE.finditer(c.text):
            indent, lang, info, body = m.group(1), m.group(2), m.group(3), m.group(4)
            if lang == "mermaid":
                continue
            bid = f"b{len(blocks) + 1}"
            title = (re.search(r'title=["\']([^"\']+)', info) or [None, ""])[1]
            before = c.text[max(0, m.start() - 1500):m.start()]
            tabs = list(_TAB.finditer(before))
            tab = tabs[-1].group(1).strip() if tabs else ""   # the tab this block sits in (TabItem labels)
            label = " \u00b7 ".join(x for x in (tab, title) if x) or lang or "code"
            code = "\n".join(line[len(indent):] if line.startswith(indent) else line.lstrip() for line in body.split("\n"))
            blocks[bid] = Block(bid, lang, label, code, c.doc_id, c.title, c.section)
            out.append(c.text[pos:m.start()] + f"{indent}[code {bid} \u00b7 {lang or 'text'} \u00b7 {label}]\n")
            pos = m.start()
        out.append(c.text[pos:])
        c.text = "".join(out)
    return blocks


@dataclass
class Corpus:
    index: BM25Index
    pages: int
    sections: int
    source: str
    toc: str = ""   # one line per guide page: [title](url): description
    blocks: dict[str, Block] = field(default_factory=dict)   # code blocks by id, quoted verbatim by show_code
    pages_by_url: dict[str, tuple[str, str]] = field(default_factory=dict)   # url -> (title, description)
    section_of: dict[str, str] = field(default_factory=dict)   # section address -> its heading
    chunks: list[Chunk] = field(default_factory=list)

    def correct(self, query: str) -> str:
        """Add the closest docs word for every word the docs never use (typos, misspellings)."""
        import difflib

        from formguide.knowledge.index import stems

        vocab = getattr(self, "_vocab", None)
        if vocab is None:
            chunks = getattr(self.index, "_by_ns", {}).get(NS, {}).values()
            vocab = sorted({t for c in chunks for t in stems(f"{c.section} {c.text}")})
            self._vocab = vocab
        known = set(vocab)
        extra = []
        for t in stems(query):
            if t not in known and len(t) >= 4:
                extra += difflib.get_close_matches(t, vocab, n=1, cutoff=0.75)
        return f"{query} {' '.join(extra)}" if extra else query

    def search(self, query: str, k: int = 6) -> list[Chunk]:
        """Guides first: a spec passage counts for less than a guide passage with the same score. A word the
        docs never use is corrected to the closest one they do ("pthon" -> "python")."""
        query = self.correct(query)
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
        # cut only between blocks outside code: the state before this block counts, so a long code block stays whole
        if len(cur) + len(block) > size and cur and not in_code:
            out.append(cur.strip())
            cur = ""
        if block.count("```") % 2:
            in_code = not in_code
        cur += block + "\n\n"
    if cur.strip():
        out.append(cur.strip())
    return out


def read(source: str, timeout: float = 20) -> str:
    """A URL (https://.../llms-full.txt) or a local path."""
    if re.match(r"https?://", source):
        req = urllib.request.Request(source, headers={"User-Agent": "dushes-docs-ai"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — the configured docs URL
            return r.read().decode("utf-8")
    return Path(source).read_text(encoding="utf-8")


def contents(text: str) -> str:
    """The table of contents: a line per page (specifications left out), so "where is X documented?" has an answer."""
    lines = []
    marks = list(_PAGE.finditer(text))
    for i, m in enumerate(marks):
        url = m.group(1)
        if "/specifications/" in url:
            continue
        body = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        title = (re.search(r"^# (.+)$", body, re.M) or [None, url])[1]
        desc = (re.search(r"^> (.+)$", body, re.M) or [None, ""])[1]
        lines.append(f"- [{title}]({url})" + (f": {desc}" if desc else ""))
    return "\n".join(lines)


def page_index(text: str) -> dict[str, tuple[str, str]]:
    """Every page's address -> (title, one-line description)."""
    out = {}
    marks = list(_PAGE.finditer(text))
    for i, m in enumerate(marks):
        body = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        title = (re.search(r"^# (.+)$", body, re.M) or [None, m.group(1)])[1]
        desc = (re.search(r"^> (.+)$", body, re.M) or [None, ""])[1]
        out[m.group(1)] = (title, desc)
    return out


def load(source: str) -> Corpus:
    text = read(source)
    chunks = split(text)
    blocks = mark_blocks(chunks)
    if not chunks:
        raise ValueError(f"no pages in {source}: expected llms-full.txt with <!-- page: ... --> markers")
    idx = BM25Index()
    idx.add(chunks)
    return Corpus(index=idx, pages=len({c.doc_id.split('#')[0] for c in chunks}), sections=len(chunks), source=source,
                  toc=contents(text), blocks=blocks, pages_by_url=page_index(text),
                  section_of={c.doc_id: c.section for c in chunks}, chunks=chunks)
