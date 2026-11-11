"""Compile a form's business documents into its domain pack (offline, on upload).

One model pass over all documents of the form plus a catalog of the form's
fields. The output (field notes, rules, flow hints, a summary) is merged into
the DomainPack, so most questions are answered from the cheap per-turn context;
the research agent (research.py) covers the long tail.
"""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..form.layout import LayoutIndex
from ..form.overlay import Overlay
from ..models import structured
from .base import KnowledgeBase

MAX_DOC_CHARS = 600_000  # ~150K tokens; above this, compile per document instead (not needed for the demo)


class FieldNote(BaseModel):
    field: str = Field(description="exact field name from the catalog")
    note: str = Field(description="what the documents say about this field, 1-2 sentences")
    source: str = Field(description="document title and section")


class CompiledKnowledge(BaseModel):
    summary: str = Field(description="2-4 sentences: what these documents cover")
    flow_hints: list[str] = Field(description="advice on the order of filling the form, if the documents imply any")
    rules: list[str] = Field(description="business rules / eligibility conditions / limits, each self-contained, with source")
    field_notes: list[FieldNote]


SYSTEM = """You turn a business's internal documents into compact guidance for an assistant that helps end users fill in one specific form.
Rules:
- Use only facts stated in the documents. Do not add general knowledge.
- Attach a note to a field only if the documents clearly say something about it; use the exact field name from the catalog.
- Keep numbers, limits and terms exactly as written (quote original-language terms as is).
- Write in English, concisely. Every rule and note mentions its source (document title and section)."""


def field_catalog(ov: Overlay, limit: int = 400) -> str:
    lines = []
    for n in ov.layout.fields():
        e = ov[n.name]
        path = " › ".join(ov[a.name].label for a in ov.layout.ancestors(n.name) if ov[a.name].label)
        opts = ""
        if e.options:
            opts = " | options: " + ", ".join(o["name"] for o in e.options[:10])
        lines.append(f"{n.name} | {e.label or ''} | {path} | {n.role}{opts}")
    return "\n".join(lines[:limit])


async def compile_form(kb: KnowledgeBase, form_id: str, layout: LayoutIndex, config: dict,
                       model: BaseChatModel) -> dict:
    text = kb.all_text(form_id)
    if not text.strip():
        kb.save_compiled(form_id, {})
        return {}
    if len(text) > MAX_DOC_CHARS:
        raise ValueError(f"documents too large to compile in one pass ({len(text)} chars)")
    ov = Overlay(layout, config)
    k: CompiledKnowledge = await structured(model, CompiledKnowledge).ainvoke([
        SystemMessage(content=SYSTEM),
        HumanMessage(content=[
            {"type": "text", "text": f"<documents>\n{text}\n</documents>"},
            {"type": "text", "text": f"<form_fields>\nname | label | path | type\n{field_catalog(ov)}\n</form_fields>\n"
                                     "Compile the guidance for this form."},
        ]),
    ])
    if k is None:
        raise RuntimeError("compile failed: the model returned no structured output")
    known = set(layout.nodes)
    notes = {n.field: f"{n.note} ({n.source})" for n in k.field_notes if n.field in known}
    dropped = [n.field for n in k.field_notes if n.field not in known]
    data = {
        "summary": k.summary, "flow_hints": k.flow_hints, "rules": k.rules, "field_notes": notes,
        "dropped_fields": dropped, "documents": [d["filename"] for d in kb.documents_for(form_id)],
        "compiled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    kb.save_compiled(form_id, data)
    return data
