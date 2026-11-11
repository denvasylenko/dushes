"""A ready-made FastAPI app (extra `server`): the agent endpoints in one call.

    from formguide.app import create_app
    app = create_app("formguide.yaml")                  # or a GuideConfig, a FormGuide, or nothing

    uvicorn my_service:app        # or:  formguide serve --config formguide.yaml

With no argument the config comes from $FORMGUIDE_CONFIG, then ./formguide.yaml, then defaults
(the model from $FORMGUIDE_MODEL or the Anthropic defaults). The FormGuide is `app.state.guide`.
To add the endpoints to an existing FastAPI app instead, use `formguide.server.create_router`.
"""
from __future__ import annotations

import os
from pathlib import Path

from .config import GuideConfig, load_config
from .guide import FormGuide


def resolve_guide(config: GuideConfig | FormGuide | str | Path | None = None) -> FormGuide:
    if isinstance(config, FormGuide):
        return config
    if config is None:
        env = os.environ.get("FORMGUIDE_CONFIG")
        if env:
            config = env
        elif Path("formguide.yaml").exists():
            config = "formguide.yaml"
    if isinstance(config, (str, Path)):
        config = load_config(config)
    return FormGuide(config)


def create_app(config: GuideConfig | FormGuide | str | Path | None = None, *, prefix: str = "/agent",
               cors: list[str] | None = None, debug: bool = False, static_dir: str | Path | None = None):
    """FastAPI app with the agent router under `prefix`.

    cors: allowed origins (["*"] for development); static_dir: serve a built frontend at "/"."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from .server import create_router

    guide = resolve_guide(config)
    app = FastAPI(title="formguide")
    app.state.guide = guide
    if cors:
        app.add_middleware(CORSMiddleware, allow_origins=cors, allow_methods=["*"], allow_headers=["*"])
    app.include_router(create_router(guide, debug=debug), prefix=prefix)

    @app.get(f"{prefix}/health")
    def health() -> dict:
        return {"ok": True}

    if static_dir and Path(static_dir).exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return app
