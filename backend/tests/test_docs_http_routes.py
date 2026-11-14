"""Every HTTP endpoint the routers serve is in the docs' HTTP API reference, and every documented one exists.

The routes come from the real routers (create_router, create_dushes_router), not from parsing code; the docs side is
the endpoint tables of site/src/content/docs/reference/http-api.md. A new endpoint fails here until the page has it.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from formguide.server import create_router
from formguide.site import Dushes, SiteMap, create_dushes_router

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "site" / "src" / "content" / "docs" / "reference" / "http-api.md"
SITE = ROOT / "backend" / "demo" / "site.yaml"
ROW = re.compile(r"^\| `(GET|POST|PUT|PATCH|DELETE) (/[^`]*)` \|", re.M)
PARAM = re.compile(r"\{[^}]+\}")


def key(method: str, path: str) -> str:
    """Method and path with every parameter as {}: a parameter's name is the docs' to choose."""
    return f"{method} {PARAM.sub('{}', path)}"


def served(router) -> set[str]:
    return {key(m, r.path) for r in router.routes if isinstance(r, APIRoute) for m in r.methods - {"HEAD", "OPTIONS"}}


def documented(section: str) -> set[str]:
    """The endpoint rows of one part of the page: the agent's (before the Dushes heading) or Dushes'."""
    text = PAGE.read_text(encoding="utf-8")
    agent, _, rest = text.partition("\n## Dushes")
    dushes = rest.split("\n## ", 1)[0]
    part = agent if section == "agent" else dushes
    return {key(m, p) for m, p in ROW.findall(part)}


def test_every_agent_endpoint_is_documented(guide):
    routes = served(create_router(guide, debug=True))   # debug=True: the page documents /debug too
    docs = documented("agent")
    assert routes - docs == set(), f"served but not in reference/http-api.md: {sorted(routes - docs)}"
    assert docs - routes == set(), f"in reference/http-api.md but not served: {sorted(docs - routes)}"


def test_every_dushes_endpoint_is_documented(guide):
    routes = served(create_dushes_router(Dushes(guide, SiteMap.load(SITE))))
    docs = documented("dushes")
    assert routes - docs == set(), f"served but not in the Dushes table of reference/http-api.md: {sorted(routes - docs)}"
    assert docs - routes == set(), f"in the Dushes table of reference/http-api.md but not served: {sorted(docs - routes)}"
