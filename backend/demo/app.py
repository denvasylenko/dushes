"""Demo server: a mock form backend (/java) + the formguide router (/agent) + the demo frontend.

    uv run uvicorn demo.app:app --port 8000 --reload --reload-dir formguide --reload-dir demo

Only the /agent part is "the product"; /java stands in for your form backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from formguide.app import create_app

from .mock_forms import FORMS

HERE = Path(__file__).resolve().parent

# The whole agent side: one call (agent endpoints under /agent).
app = create_app(HERE / "formguide.yaml", prefix="/agent", cors=["*"], debug=True)
guide = app.state.guide

# ===================================================================== mock form backend

java = APIRouter(prefix="/java")


def _form(form_id: str):
    if form_id not in FORMS:
        raise HTTPException(404, f"unknown form {form_id}")
    return FORMS[form_id]


@java.get("/forms")
def java_forms() -> list[str]:
    return list(FORMS)


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

_DIST = HERE.parents[1] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
