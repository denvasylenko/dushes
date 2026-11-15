"""Document storage on disk, per namespace (a form id or a shared space).

  <root>/<namespace>/originals/<doc_id>__<filename>   what the manager uploaded
  <root>/<namespace>/text/<doc_id>.md                 extracted text (the researcher's read-only filesystem)
  <root>/<namespace>/chunks.json                      sections (source of truth for the search index):
                                                      {"format": 2, "chunks": [...]}; an older file is a bare list
                                                      and is cut again from text/ when it is read
  <root>/_compiled/<form_id>.json                     knowledge compiled into the domain pack

Text extraction: .md / .txt as is, .pdf via pypdf.
"""
from __future__ import annotations

import io
import json
import re
import uuid
from pathlib import Path

from .index import Chunk

SUPPORTED = {".md", ".txt", ".pdf"}
CHUNK_CHARS = 1200      # about this many characters in a section
CHUNK_OVERLAP = 150     # carried over from the section before, inside one heading
FORMAT = 2              # of chunks.json: sections with path, page and order

_PAGE = re.compile(r"^#+\s*Page (\d+)\s*$")
# a numbered heading in text that has no markdown (a PDF): "4.2 Late payment"
_NUMBERED = re.compile(r"^(\d+(?:\.\d+){0,3})\.?\s+([^\W\d_].{1,78})$", re.UNICODE)
_LIST = re.compile(r"^\s*(?:[-*+\u2022]|\d+[.)])\s+")

_SAFE = re.compile(r"[^\w.\-]+", re.UNICODE)
_NS = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"unsupported file type {ext}; supported: {', '.join(sorted(SUPPORTED))}")
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(f"## Page {i + 1}\n\n{(p.extract_text() or '').strip()}" for i, p in enumerate(reader.pages))
    return data.decode("utf-8", errors="replace")


def _blocks(lines: list[str]) -> list[tuple[str, str]]:
    """Lines of one section -> blocks (kind, text): a table, a list or a paragraph stays together."""
    out: list[tuple[str, str]] = []
    kind, buf = "", []

    def close() -> None:
        nonlocal kind, buf
        if buf:
            out.append((kind, "\n".join(buf)))
        kind, buf = "", []

    for line in lines:
        if not line.strip():
            close()
            continue
        k = "table" if line.lstrip().startswith("|") else "list" if _LIST.match(line) else "text"
        if k == "text" and kind == "list" and line.startswith((" ", "\t")):
            k = "list"   # a list item that goes on
        if buf and k != kind:
            close()
        kind = k
        buf.append(line)
    close()
    return out


def _tail(text: str, overlap: int) -> str:
    """The end of a section to repeat at the start of the next: whole lines or sentences, up to `overlap` chars."""
    if overlap <= 0 or len(text) <= overlap:
        return ""
    cut = text[-overlap:]
    for mark in ("\n", ". ", "; "):
        i = cut.find(mark)
        if 0 <= i < len(cut) - 20:
            return cut[i + len(mark):].strip()
    return cut.split(" ", 1)[-1].strip()


def chunk_text(namespace: str, doc_id: str, text: str, chunk_chars: int = CHUNK_CHARS,
               overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """A document's text -> sections: cut on headings, then on paragraphs to about `chunk_chars` with `overlap`
    characters shared by neighbours under one heading. A table or a list stays whole while it fits twice the
    size. Each section keeps its heading path, its page (a PDF's "## Page N" lines) and its order."""
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else doc_id
    paged = any(_PAGE.match(ln) for ln in lines)
    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []        # (level, heading) from the document's top down
    page: int | None = None
    body: list[str] = []
    body_page: int | None = None

    def flush() -> None:
        nonlocal body, body_page
        path = " > ".join(h for _lv, h in stack)
        section = stack[-1][1] if stack else (f"Page {body_page}" if body_page else title)
        buf, carried = "", ""

        def emit() -> None:
            nonlocal buf, carried
            if buf.strip() and buf.strip() != carried:
                chunks.append(Chunk(f"{doc_id}#{len(chunks)}", namespace, doc_id, title, section, buf.strip(),
                                    path=path or section, page=body_page, order=len(chunks)))
            carried = _tail(buf.strip(), overlap)
            buf = carried + "\n" if carried else ""

        for kind, block in _blocks(body):
            whole = kind in ("table", "list") and len(block) <= 2 * chunk_chars
            parts = [block] if whole or len(block) <= chunk_chars else block.split("\n")
            for part in parts:
                while len(part) > 2 * chunk_chars:   # one endless line: cut it at a space
                    cut = part.rfind(" ", 0, chunk_chars)
                    cut = cut if cut > chunk_chars // 2 else chunk_chars
                    if buf.strip() and buf.strip() != carried:
                        emit()
                    buf += part[:cut] + "\n"
                    emit()
                    part = part[cut:].lstrip()
                if buf.strip() and buf.strip() != carried and len(buf) + len(part) > chunk_chars:
                    emit()
                buf += part + "\n"
            if kind != "text" or len(parts) == 1:
                buf += "\n" if not buf.endswith("\n\n") else ""
        if buf.strip() and buf.strip() != carried:
            carried = ""
            emit()
        body, body_page = [], None

    for i, line in enumerate(lines):
        m = _PAGE.match(line)
        if m:                                   # a page break of a PDF: not a heading of the document
            if not stack:                       # no headings found yet: the page is the only landmark
                flush()
            page = int(m.group(1))
            continue
        level, heading = 0, ""
        if line.startswith("#"):
            level, heading = len(line) - len(line.lstrip("#")), line.lstrip("# ").strip()
        elif paged:
            n = _NUMBERED.match(line.strip())
            if n and not line.rstrip().endswith((".", ",", ";", ":")):
                level, heading = 1 + n.group(1).count("."), line.strip()
        if level and heading:
            flush()
            if i == 0:                          # the document's own title line is not part of the path
                continue
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
            continue
        if not body:
            body_page = page
        body.append(line)
    flush()
    return chunks


class DocumentStore:
    def __init__(self, root: str | Path, chunk_chars: int = CHUNK_CHARS, chunk_overlap: int = CHUNK_OVERLAP):
        self.root = Path(root)
        self.chunk_chars = max(200, int(chunk_chars))
        self.chunk_overlap = max(0, min(int(chunk_overlap), self.chunk_chars // 2))
        self.recut: dict[str, list[Chunk]] = {}   # namespace -> the sections an older chunks.json held, replaced now

    def ns_dir(self, namespace: str) -> Path:
        if not _NS.match(namespace):
            raise ValueError(f"invalid namespace {namespace!r}")
        return self.root / namespace

    def text_dir(self, namespace: str) -> Path:
        return self.ns_dir(namespace) / "text"

    def namespaces(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir() and _NS.match(p.name)) if self.root.exists() else []

    # ------------------------------------------------------------ documents
    def add(self, namespace: str, filename: str, data: bytes) -> tuple[dict, list[Chunk]]:
        safe = _SAFE.sub("_", Path(filename).name)[:120] or "document"
        text = extract_text(safe, data)
        doc_id = uuid.uuid4().hex[:8]
        d = self.ns_dir(namespace)
        (d / "originals").mkdir(parents=True, exist_ok=True)
        self.text_dir(namespace).mkdir(parents=True, exist_ok=True)
        (d / "originals" / f"{doc_id}__{safe}").write_bytes(data)
        full = f"# {safe}\n\n{text}"
        (self.text_dir(namespace) / f"{doc_id}.md").write_text(full)
        new = chunk_text(namespace, doc_id, full, self.chunk_chars, self.chunk_overlap)
        self._save_chunks(namespace, self.chunks(namespace) + new)
        return {"doc_id": doc_id, "namespace": namespace, "filename": safe, "chars": len(text)}, new

    def list(self, namespace: str) -> list[dict]:
        orig = self.ns_dir(namespace) / "originals"
        if not orig.exists():
            return []
        out = []
        for p in sorted(orig.iterdir()):
            doc_id, _, name = p.name.partition("__")
            txt = self.text_dir(namespace) / f"{doc_id}.md"
            out.append({"doc_id": doc_id, "namespace": namespace, "filename": name, "bytes": p.stat().st_size,
                        "chars": len(txt.read_text()) if txt.exists() else 0})
        return out

    def delete(self, namespace: str, doc_id: str) -> list[Chunk]:
        """Delete a document; returns its chunks (to remove them from the index)."""
        d = self.ns_dir(namespace)
        for p in list((d / "originals").glob(f"{doc_id}__*")) + [self.text_dir(namespace) / f"{doc_id}.md"]:
            if p.exists():
                p.unlink()
        all_chunks = self.chunks(namespace)
        gone = [c for c in all_chunks if c.doc_id == doc_id]
        self._save_chunks(namespace, [c for c in all_chunks if c.doc_id != doc_id])
        return gone

    def all_text(self, namespaces: list[str]) -> str:
        parts = []
        for ns in namespaces:
            d = self.text_dir(ns)
            if d.exists():
                parts += [p.read_text() for p in sorted(d.glob("*.md"))]
        return "\n\n".join(parts)

    # ------------------------------------------------------------ chunks
    def chunks(self, namespace: str) -> list[Chunk]:
        p = self.ns_dir(namespace) / "chunks.json"
        if not p.exists():
            return []
        raw = json.loads(p.read_text())
        if isinstance(raw, dict) and raw.get("format") == FORMAT:
            return [Chunk(**{"namespace": namespace, **c}) for c in raw.get("chunks") or []]
        # an older file (a bare list, sections without path or page): cut every document again from its stored text
        old = [Chunk(**{"namespace": namespace, **{k: v for k, v in c.items() if k in Chunk.__dataclass_fields__}})
               for c in (raw if isinstance(raw, list) else raw.get("chunks") or [])]
        new: list[Chunk] = []
        d = self.text_dir(namespace)
        for txt in sorted(d.glob("*.md")) if d.exists() else []:
            new += chunk_text(namespace, txt.stem, txt.read_text(), self.chunk_chars, self.chunk_overlap)
        self._save_chunks(namespace, new)
        self.recut[namespace] = old
        return new

    def _save_chunks(self, namespace: str, chunks: list[Chunk]) -> None:
        self.ns_dir(namespace).mkdir(parents=True, exist_ok=True)
        (self.ns_dir(namespace) / "chunks.json").write_text(
            json.dumps({"format": FORMAT, "chunks": [c.to_dict() for c in chunks]}, ensure_ascii=False))

    # ------------------------------------------------------------ compiled knowledge (per form)
    def save_compiled(self, form_id: str, data: dict) -> None:
        d = self.root / "_compiled"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{self.ns_dir(form_id).name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))

    def load_compiled(self, form_id: str) -> dict | None:
        try:
            p = self.root / "_compiled" / f"{self.ns_dir(form_id).name}.json"
        except ValueError:
            return None
        legacy = self.root / form_id / "compiled.json"   # pre-namespace layout
        for q in (p, legacy):
            if q.exists():
                return json.loads(q.read_text())
        return None
