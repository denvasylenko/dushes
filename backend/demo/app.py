"""Demo server: a mock form backend (/java) + the formguide router (/agent) + the demo frontend.

    uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo

Only the /agent part is "the product"; /java stands in for your form backend.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from formguide.app import create_app

from .mock_forms import FORMS
from .mock_forms.lab import LAB

HERE = Path(__file__).resolve().parent

# The whole agent side: one call (agent endpoints under /agent). DEMO_CONFIG picks another config file
# (the hosted demo uses formguide.hosted.yaml); DEMO_DEBUG=0 turns the debug endpoint off.
app = create_app(Path(os.environ.get("DEMO_CONFIG") or HERE / "formguide.yaml"), prefix="/agent", cors=["*"],
                 debug=os.environ.get("DEMO_DEBUG", "1") != "0")
guide = app.state.guide

# ===================================================================== mock form backend

java = APIRouter(prefix="/java")


def _form(form_id: str):
    if form_id not in FORMS:
        raise HTTPException(404, f"unknown form {form_id}")
    return FORMS[form_id]


@java.get("/forms")
def java_forms() -> list[str]:
    return [f for f in FORMS if f not in LAB]   # the demo page's picker; the Lab's forms are on /lab


@java.get("/form")
def java_form(form_id: str = "loan_application") -> dict:
    f = _form(form_id)
    return {"form_id": f.form_id, "jsx": f.jsx, "config": f.compute(None), "domain": f.domain}


class JavaEvent(BaseModel):
    form_id: str = "loan_application"
    state: dict[str, Any]
    changes: dict[str, Any] = Field(default_factory=dict)


@java.post("/event")
def java_event(ev: JavaEvent) -> dict:
    return _form(ev.form_id).compute({**ev.state, **ev.changes})


app.include_router(java)

@app.middleware("http")
async def no_stale_page(request, call_next):
    """The page itself is never cached, so a rebuilt frontend shows up on a normal reload."""
    response = await call_next(request)
    if not request.url.path.startswith(("/assets/", "/agent/", "/java/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


# The chat widget's one-script build and the plain-HTML example (examples/widget-html):
# http://localhost:8000/examples/widget/ after `cd packages/agui-chat && npm run build`.
_WIDGET = HERE.parents[1] / "packages" / "agui-chat" / "dist"
if _WIDGET.exists():
    app.mount("/widget", StaticFiles(directory=_WIDGET), name="widget")
_EXAMPLE = HERE.parents[1] / "examples" / "widget-html"
if _EXAMPLE.exists():
    app.mount("/examples/widget", StaticFiles(directory=_EXAMPLE, html=True), name="widget-example")
# The react-hook-form example: http://localhost:8000/examples/react-hook-form/ after
# `cd examples/react-hook-form && npm install && npm run build`.
_RHF = HERE.parents[1] / "examples" / "react-hook-form" / "dist"
if _RHF.exists():
    app.mount("/examples/react-hook-form", StaticFiles(directory=_RHF, html=True), name="rhf-example")

# Dushes over a multi-page demo site (frontend/site.html, demo/site.yaml): /site/run, /site/map.
from .site_app import mount as mount_site  # noqa: E402

mount_site(app, guide)

# The Form Lab: Dushes over the QA library of forms (demo/mock_forms/lab/), for the scenario evals: /lab/run, /lab/map.
from .lab_site import mount as mount_lab  # noqa: E402

mount_lab(app, guide)

# The demo page at "/" (DEMO_PATH moves it, e.g. "/demo" on the docs host, built with `vite build --base /demo/`).
_DIST = HERE.parents[1] / "frontend" / "dist"
if _DIST.exists():
    app.mount(os.environ.get("DEMO_PATH", "/"), StaticFiles(directory=_DIST, html=True), name="frontend")
