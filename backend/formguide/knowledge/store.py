"""Document storage on disk, per namespace (a form id or a shared space).

  <root>/<namespace>/originals/<doc_id>__<filename>   what the manager uploaded
  <root>/<namespace>/text/<doc_id>.md                 extracted text (the researcher's read-only filesystem)
  <root>/<namespace>/chunks.json                      sections (source of truth for the search index)
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
CHUNK_CHARS = 1200

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


def chunk_text(namespace: str, doc_id: str, text: str) -> list[Chunk]:
    title = text.splitlines()[0].lstrip("# ").strip() if text else doc_id
    chunks: list[Chunk] = []
    section, buf = title, ""

    def emit() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append(Chunk(f"{doc_id}#{len(chunks)}", namespace, doc_id, title, section, buf.strip()))
        buf = ""

    for line in text.splitlines():
        if line.startswith("#"):
            emit()
            section = line.lstrip("# ").strip() or section
            continue
        if len(buf) + len(line) > CHUNK_CHARS:
            emit()
        buf += line + "\n"
    emit()
    return chunks


class DocumentStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

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
        new = chunk_text(namespace, doc_id, full)
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
        # older files have no "namespace": it is the folder they live in
        return [Chunk(**{"namespace": namespace, **c}) for c in json.loads(p.read_text())] if p.exists() else []

    def _save_chunks(self, namespace: str, chunks: list[Chunk]) -> None:
        self.ns_dir(namespace).mkdir(parents=True, exist_ok=True)
        (self.ns_dir(namespace) / "chunks.json").write_text(
            json.dumps([c.to_dict() for c in chunks], ensure_ascii=False))

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
