"""Domain packs: knowledge about a specific form, resolved by form_id.

The agent core knows nothing about any domain. A pack is resolved in this order:
1. inline:   shipped together with the form (POST /layouts {domain}) -> register()
2. provider: your callable form_id -> dict | None (e.g. read from your database)
3. packs:    a dict {form_id: pack dict} passed in code
4. dir:      JSON files <dir>/<form_id>.json
5. default:  a neutral pack, so an unknown form still works

On top of the winning pack, knowledge compiled from the form's business documents
(see formguide.knowledge) is merged in: field notes, rules, flow hints, documents.

Pack shape (every field optional):
{"form_id", "title", "persona", "flow_hints": [...], "glossary": {field: note}, "pii": [field, ...], "rules": [...]}
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..knowledge.base import KnowledgeBase

log = logging.getLogger("formguide")

DEFAULT_PERSONA = "You are a helpful assistant that guides the user through filling in this form."


@dataclass
class DomainPack:
    form_id: str
    title: str = "Form"
    persona: str = DEFAULT_PERSONA
    flow_hints: list[str] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)
    pii: set[str] = field(default_factory=set)
    rules: list[str] = field(default_factory=list)       # business rules (pack + compiled documents)
    kb_summary: str = ""                                  # what the form's documents cover
    kb_documents: list[str] = field(default_factory=list)
    source: str = "default"   # inline | provider | packs | dir | default, "+kb" when documents are merged

    @classmethod
    def from_dict(cls, d: dict[str, Any], form_id: str | None = None, source: str = "inline") -> "DomainPack":
        fid = d.get("form_id") or form_id or "unknown"
        return cls(
            form_id=fid,
            title=str(d.get("title") or fid.replace("_", " ").capitalize()),
            persona=str(d.get("persona") or DEFAULT_PERSONA),
            flow_hints=[str(x) for x in d.get("flow_hints") or []],
            glossary={str(k): str(v) for k, v in (d.get("glossary") or {}).items()},
            pii={str(x) for x in d.get("pii") or []},
            rules=[str(x) for x in d.get("rules") or []],
            source=source,
        )


class DomainPackRegistry:
    def __init__(self, *, packs: dict[str, dict[str, Any]] | None = None, directory: str | Path | None = None,
                 provider: Callable[[str], dict[str, Any] | None] | None = None):
        self._static = dict(packs or {})
        self._dir = Path(directory) if directory else None
        self._provider = provider
        self._inline: dict[str, DomainPack] = {}
        self._file_cache: dict[str, DomainPack] = {}
        self.knowledge: KnowledgeBase | None = None   # set by FormGuide

    def register(self, form_id: str, data: dict[str, Any]) -> DomainPack:
        """A pack shipped together with the form (highest priority)."""
        pack = DomainPack.from_dict(data, form_id, source="inline")
        self._inline[form_id] = pack
        return pack

    def _base(self, fid: str) -> DomainPack:
        if fid in self._inline:
            return self._inline[fid]
        if self._provider:
            d = self._provider(fid)
            if d:
                return DomainPack.from_dict(d, fid, source="provider")
        if fid in self._static:
            return DomainPack.from_dict(self._static[fid], fid, source="packs")
        if self._dir:
            if fid not in self._file_cache:
                path = self._dir / f"{fid}.json"
                if path.is_file():
                    try:
                        self._file_cache[fid] = DomainPack.from_dict(json.loads(path.read_text()), fid, source="dir")
                    except (OSError, ValueError) as e:
                        log.warning("bad domain pack %s: %s", path, e)
            if fid in self._file_cache:
                return self._file_cache[fid]
        return DomainPack(form_id=fid, title=fid.replace("_", " ").capitalize())

    def available(self) -> list[str]:
        """Form ids with a configured pack (inline, static or files; a provider is asked on demand)."""
        ids = set(self._inline) | set(self._static)
        if self._dir and self._dir.is_dir():
            ids |= {p.stem for p in self._dir.glob("*.json")}
        return sorted(ids)

    def get(self, form_id: str | None) -> DomainPack:
        base = self._base(form_id or "unknown")
        return self._with_knowledge(base)

    def _with_knowledge(self, base: DomainPack) -> DomainPack:
        kb = self.knowledge
        if kb is None:
            return base
        try:
            docs = [d["filename"] for d in kb.documents_for(base.form_id)]
        except ValueError:
            return base
        k = kb.compiled(base.form_id) or {}
        if not docs and not k:
            return base
        glossary = dict(base.glossary)
        for name, note in (k.get("field_notes") or {}).items():
            glossary[name] = f"{glossary[name]} Docs: {note}" if name in glossary else note
        return replace(
            base,
            glossary=glossary,
            flow_hints=base.flow_hints + list(k.get("flow_hints") or []),
            rules=base.rules + list(k.get("rules") or []),
            kb_summary=k.get("summary", ""),
            kb_documents=docs,
            source=base.source + "+kb",
        )


def validate_pack(pack: DomainPack, known_names: set[str]) -> list[str]:
    """Warn about glossary / pii keys that do not exist in the form layout."""
    return [f"domain pack references unknown field: {k}"
            for k in sorted((set(pack.glossary) | pack.pii) - known_names)]
