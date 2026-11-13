"""The demo site's assistant: Dushes over the demo's form guide and site.yaml, at /site.

    POST /site/run   AG-UI run with state {page: {path}, form?: {config, jsx_hash, form_id, ui}}
    GET  /site/map   the site map the demo page renders (frontend/site.html)
"""
from __future__ import annotations

from pathlib import Path

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
    return site
