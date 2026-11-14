"""The Form Lab: the QA library of demo forms for the scenario evals (backend/evals/lab_*.yaml, heldout_lab_*.yaml).

Every module in this package is one form (see engine.py for what a module defines); they are found on import,
so adding a form is adding a file. `LAB` maps form ids to compiled forms; `site_map()` is the Lab site (one page
per form) that Dushes serves at /lab in the demo server (demo/lab_site.py).
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from .engine import LabForm

LAB: dict[str, LabForm] = {}

for _m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    if _m.name == "engine" or _m.name.startswith("_"):
        continue
    mod = importlib.import_module(f"{__name__}.{_m.name}")
    fid = mod.FORM_ID
    if fid in LAB:
        raise ValueError(f"lab form id {fid} is used twice ({_m.name})")
    page = {**mod.PAGE, "form": fid}
    LAB[fid] = LabForm(fid, mod.FORM, getattr(mod, "rules", None), sequential=getattr(mod, "SEQUENTIAL", False),
                       domain=getattr(mod, "DOMAIN", None), page=page, jsx=getattr(mod, "FORM_JSX", None))

HOME = {
    "path": "/",
    "title": "Form Lab",
    "description": "Form Lab, a test portal with many unrelated businesses and one form each.",
    "sections": [{"id": "about", "title": "About Form Lab",
                  "text": "Every page belongs to a different, unrelated business and holds one form. "
                          "Ask the assistant which form you need, or open the page of the business."}],
}


def site_map() -> dict[str, Any]:
    """The Lab site: a home page and each form's page, as a site-map dict (formguide.site.SiteMap.load)."""
    paths = [f.page["path"] for f in LAB.values()]
    dup = {p for p in paths if paths.count(p) > 1}
    if dup:
        raise ValueError(f"lab page paths used twice: {sorted(dup)}")
    return {"title": "Form Lab",
            "instructions": "Each page is a separate business: never mix one business's prices, rules or hours "
                            "with another's. A business's facts are only those on its own page and in its form.",
            "pages": [HOME, *(f.page for f in LAB.values())]}
