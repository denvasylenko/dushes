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

# A tool that always fails, for the QA scenarios about what the assistant says after a tool error. Only on a
# stand that asks for it; the public demo never has it.
if os.environ.get("DEMO_FAILING_TOOL") == "1":
    from .skill_tools import check_promo_code  # noqa: E402

    guide._tools.append(check_promo_code)

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

# Experimental features behind an activation code (EXPERIMENT_CODES): on a host that sets it, the decision model
# runs only for a visitor who entered a code; without a pass nothing is sent to the chooser, and no label or
# decision trace is shown. A host without the setting is not gated (a developer's machine).
from formguide import experiments as _experiments  # noqa: E402

_EXPERIMENTS = _experiments.Experiments.from_env()
if _EXPERIMENTS.enabled:
    _experiments.install(app, _EXPERIMENTS)
    app.include_router(_experiments.create_experiments_router(_EXPERIMENTS), prefix="/experiments")

# The Form Lab: Dushes over the QA library of forms (demo/mock_forms/lab/), for the scenario evals: /lab/run, /lab/map.
from .lab_site import mount as mount_lab  # noqa: E402

mount_lab(app, guide)

# The demo page at "/" (DEMO_PATH moves it, e.g. "/demo" on the docs host, built with `vite build --base /demo/`).
_DIST = HERE.parents[1] / "frontend" / "dist"

# The owner's local demo of the choice layer (demo branch, DEMO_OUR_VOICE=1): the microphone is our own Whisper in
# every browser (the page's ?dictation=server switch, set by a redirect), and the chat has no "add files" button.
if os.environ.get("DEMO_OUR_VOICE") == "1" and (_DIST / "site.html").exists():
    from fastapi import Request as _Request
    from fastapi.responses import HTMLResponse as _HTML
    from fastapi.responses import RedirectResponse as _Redirect

    # the talking mode (the same one as on the form demo) when this host has voice codes: its routes, and the
    # widget's voice mode switched on for the site page's chat
    _TALK = ""
    if os.environ.get("VOICE_CODES"):
        from formguide import voice as _voice
        _VOICE = _voice.Talks(_voice.VoiceConfig.from_env(), title="the Main Street demo",
                              log_dir=Path(guide.data_dir) / "voice", stop=guide.stop)
        if _VOICE.config.enabled:
            app.include_router(_voice.create_voice_router(_voice.watch(_VOICE)), prefix="/voice")
            _EXPERIMENTS.join("voice", _VOICE.gate)     # one code field opens both
            _TALK = "if(c&&!c.hasAttribute('voice-mode'))c.setAttribute('voice-mode','true');"

    _NO_FILES = ("<script>customElements.whenDefined('agui-chat').then(()=>{const set=()=>{const c="
                 "document.querySelector('agui-chat');if(c&&c.getAttribute('attach')!=='false')"
                 "c.setAttribute('attach','false');" + _TALK + "};set();new MutationObserver(set).observe("
                 "document.documentElement,{childList:true,subtree:true})})</script>")

    @app.get(os.environ.get("DEMO_PATH", "/").rstrip("/") + "/site.html", include_in_schema=False)
    def _site_page(request: _Request):
        if request.query_params.get("dictation") != "server":
            return _Redirect(str(request.url.include_query_params(dictation="server")))
        page = (_DIST / "site.html").read_text(encoding="utf-8")
        return _HTML(page.replace("</body>", _NO_FILES + "</body>"), headers={"Cache-Control": "no-store"})

if _DIST.exists():
    app.mount(os.environ.get("DEMO_PATH", "/"), StaticFiles(directory=_DIST, html=True), name="frontend")
