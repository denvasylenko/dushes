"""The demo site's assistant: Dushes over the demo's form guide and site.yaml, at /site.

    POST /site/run   AG-UI run with state {page: {path}, form?: {config, jsx_hash, form_id, ui}}
    GET  /site/map   the site map the demo page renders (frontend/site.html)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from formguide import experiments as _experiments
from formguide.site import Dushes, SiteMap, create_dushes_router

SITE_MAP = Path(__file__).with_name("site.yaml")


SITE_DOCS = Path(__file__).parent / "samples" / "kb" / "site"


def form_for(guide):
    """The form's state on the server (the mock form backend's defaults, as the page loads them), so the form
    agent answers in the same run as Dushes' open_form."""
    def build(form_id: str, ctx) -> dict | None:
        from .app import _form   # the mock form backend of the demo
        try:
            f = _form(form_id)
        except Exception:  # noqa: BLE001 — an unknown form: the page's own hand-off run
            return None
        reg = guide.register_form(f.jsx, f.form_id, f.domain)
        return {"config": f.compute(None), "jsx_hash": reg["jsx_hash"], "form_id": f.form_id,
                "ui": {"activeTabs": {}, "openAccordions": [], "focused": None}}
    return build


def mount(app, guide) -> Dushes:
    site = Dushes(guide, SiteMap.load(SITE_MAP), suggestions=True, form_for=form_for(guide))
    # the site's own documents (partners, glossary) for Dushes; the forms keep theirs
    if not guide.knowledge.list_documents("site"):
        for doc in sorted(SITE_DOCS.glob("*.md")):
            guide.add_document("site", doc.name, doc.read_bytes())
    app.include_router(create_dushes_router(site), prefix="/site")
    app.state.site = site
    if os.environ.get("INTENT_PROVIDER") and os.environ.get("INTENT_FORM_PAGE", "1") != "0":
        front_forms(guide, site)
    return site


def front_forms(guide, site: Dushes) -> None:
    """The choice layer in front of a form that is talked to directly (the "Form + assistant" page, /agent/run),
    with no site assistant: the owner asked for it by name (2026-11-17). The same layer as on the site, asked
    about the form on the screen only: values, dates, sections, "all the sections". What it is sure of becomes the
    UI agent's decided steps (its own card, its own "show" step); anything else, and any move to another
    page, is the UI agent's turn as before. The label and the decision trace follow the run, as on the site."""
    import uuid

    from formguide.site.guide import _decision_trace
    from formguide.stats import RunStats, model_id

    inner = guide.run
    guide._layer_front = True

    async def run(thread_id, *, message=None, state=None, resume=None, **kw):
        from_site = kw.pop("_from_site", False)
        stats = RunStats(kw.get("run_id") or "", thread_id)
        fast = None
        page = next((p for p in site.site.pages if isinstance(state, dict) and p.form == state.get("form_id")), None)
        # INTENT_LAYER=0 (the "agent alone" arm) turns the layer off here as on the site
        if (message and resume is None and not from_site and page is not None and state.get("config")
                and os.environ.get("INTENT_LAYER", "1") != "0"):
            try:
                fast = await site._fast(thread_id, message, {"page": {"path": page.path}, "form": state}, stats, form_thread=thread_id)
            except Exception:  # noqa: BLE001 - the layer never breaks a turn of the form
                fast = None
            if fast and fast["kind"] not in ("value", "focus"):
                # a move to another page, or "the site assistant's turn": this page has neither; the form's UI agent answers
                fast = None
                if getattr(stats, "fast", None):
                    stats.fast["handled"] = False
        seen = {"screen": []}
        async for ev in inner(thread_id, message=message, state=state, resume=resume, **kw):
            if ev.get("type") == "CUSTOM" and ev.get("name") in ("ui_directive", "on_interrupt"):
                value = ev.get("value")
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        value = None
                seen["screen"].append({"name": ev["name"], "value": value})
            if ev.get("type") in ("RUN_FINISHED", "RUN_ERROR") and getattr(stats, "fast", None):
                asked = stats.fast
                if os.environ.get("INTENT_LABELS") == "1" and _experiments.allowed():
                    who = site.intent.settings.provider.capitalize()
                    name = str(model_id(guide.models.agent) or "")
                    label = (f"{who} \u00b7 {asked['ms']} ms" if asked.get("handled") else
                             f"{'Haiku' if 'haiku' in name.lower() else name} \u00b7 {RunStats.now() - stats.t0:.1f} s "
                             f"(after {who} {asked['ms']} ms: not sure)")
                    lid = f"label_{uuid.uuid4().hex[:10]}"
                    yield {"type": "TEXT_MESSAGE_START", "messageId": lid, "role": "assistant"}
                    yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": lid, "delta": f"\u2014 {label}"}
                    yield {"type": "TEXT_MESSAGE_END", "messageId": lid}
                if os.environ.get("INTENT_TRACE") == "1" and _experiments.allowed() and getattr(stats, "trace", None):
                    more = thread_id in site.__dict__.get("_mixed", {})
                    yield {"type": "CUSTOM", "name": "decision_trace",
                           "value": _decision_trace(stats, seen, kw.get("run_id") or "", more, site.site)}
            yield ev

    guide.run = run
