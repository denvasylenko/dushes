"""The demo site's assistant: SiteGuide over the demo's form guide and site.yaml, at /site.

    POST /site/run   AG-UI run with state {page: {path}, form?: {config, jsx_hash, form_id, ui}}
    GET  /site/map   the site map the demo page renders (frontend/site.html)
"""
from __future__ import annotations

from pathlib import Path

from formguide.site import SiteGuide, SiteMap, create_site_router

SITE_MAP = Path(__file__).with_name("site.yaml")


def mount(app, guide) -> SiteGuide:
    site = SiteGuide(guide, SiteMap.load(SITE_MAP))
    app.include_router(create_site_router(site), prefix="/site")
    app.state.site = site
    return site
