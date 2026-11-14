"""The Form Lab site: Dushes over the QA library of forms (demo/mock_forms/lab/), at /lab.

    POST /lab/run   AG-UI run, like /site/run
    GET  /lab/map   the Lab site map

A second site next to Main Street (/site), so the scenario evals can exercise many forms without changing the
demo site people see. The two share one form guide (models, checkpointer, transcripts).
"""
from __future__ import annotations

from formguide.site import Dushes, SiteMap, create_dushes_router

from .mock_forms.lab import site_map
from .site_app import form_for


def mount(app, guide) -> Dushes:
    lab = Dushes(guide, SiteMap.load(site_map()), suggestions=True, form_for=form_for(guide))
    app.include_router(create_dushes_router(lab), prefix="/lab")
    app.state.lab = lab
    return lab
