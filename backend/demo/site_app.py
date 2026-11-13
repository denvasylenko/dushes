"""The demo site's assistant: SiteGuide over the demo's form guide and site.yaml, at /site.

    POST /site/run   AG-UI run with state {page: {path}, form?: {config, jsx_hash, form_id, ui}}
    GET  /site/map   the site map the demo page renders (frontend/site.html)
"""
from __future__ import annotations

from pathlib import Path

from formguide.site import SiteGuide, SiteMap, create_site_router

SITE_MAP = Path(__file__).with_name("site.yaml")


SITE_DOCS = Path(__file__).parent / "samples" / "kb" / "site"


def mount(app, guide) -> SiteGuide:
    site = SiteGuide(guide, SiteMap.load(SITE_MAP))
    # the site's own documents (partners, glossary) for the site agent; the forms keep theirs
    if not guide.knowledge.list_documents("site"):
        for doc in sorted(SITE_DOCS.glob("*.md")):
            guide.add_document("site", doc.name, doc.read_bytes())
    app.include_router(create_site_router(site), prefix="/site")
    app.state.site = site
    return site
