"""Find fields by meaning ("where do I enter my tax id?").

Demo version: lexical search over label, name, path and glossary with crude
stemming (truncate words to 5 chars), which works for any language. In
production add embeddings and cache the index by (jsx_hash, labels hash).
"""
from __future__ import annotations

import re

from ..domain.packs import DomainPack
from .overlay import Overlay

_WORD = re.compile(r"\w+", re.UNICODE)


def _stems(text: str) -> set[str]:
    # normalize Cyrillic yo to ye so both spellings match
    words = _WORD.findall(text.lower().replace("\u0451", "\u0435").replace("_", " "))
    return {w[:5] if len(w) > 5 else w for w in words if len(w) > 1}


def search(ov: Overlay, pack: DomainPack, query: str, limit: int = 8) -> list[tuple[float, str]]:
    q = _stems(query)
    if not q:
        return []
    scored = []
    for n in ov.layout.fields():
        e = ov[n.name]
        path = " ".join(ov[a.name].label or "" for a in ov.layout.ancestors(n.name))
        main = _stems(f"{e.label or ''} {n.name.replace('_', ' ')}")
        extra = _stems(f"{path} {pack.glossary.get(n.name, '')}")
        s = 2 * len(q & main) + 0.5 * len(q & extra)
        if s:
            s += 0.3 if e.visible else 0
            scored.append((s, n.name))
    scored.sort(key=lambda x: -x[0])
    return scored[:limit]
