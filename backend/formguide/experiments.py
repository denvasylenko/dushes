"""Experimental features behind an activation code.

A host that sets EXPERIMENT_CODES ("anna=<code>,ben=<code>", the same shape as VOICE_CODES, a separate list) keeps
its experimental features off for everyone except a person who entered a code. The first such feature is the
decision model (the choice layer, `formguide.intent`): without a pass the layer is not asked at all, so nothing a
visitor writes leaves the server for the chooser's supplier, and no label or decision trace is sent.

    exp = Experiments.from_env()
    if exp.enabled:
        install(app, exp)                                          # reads the pass of every request
        app.include_router(create_experiments_router(exp), prefix="/experiments")

    GET  /experiments            -> {"features": [...], "unlocked": bool}      what a code would open here
    POST /experiments/unlock     {code} -> {"person", "pass", "features"}      403 for a wrong code

The pass travels in the X-Experiment-Pass header of a run request, never in an address. A host that installs no
gate is not gated: its own settings alone decide (a developer's machine, a test stand).
"""
from __future__ import annotations

import contextvars
import os
from typing import Any

from . import voice as _voice

try:
    from fastapi import APIRouter, HTTPException, Request
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - the core works without the server extra
    APIRouter = None  # type: ignore[assignment,misc]
    BaseModel = object  # type: ignore[assignment,misc]

HEADER = "x-experiment-pass"
DECISION_MODEL = "decision_model"

_gated = False                                   # whether this process has a gate installed
_person: contextvars.ContextVar[str | None] = contextvars.ContextVar("experiment_person", default=None)


class _Codes:
    """What `voice.Gate` needs of a configuration: the codes and the signing secret."""

    def __init__(self, codes: dict[str, str], secret: str):
        self.codes, self.secret = codes, secret


class Experiments:
    """The codes of a host and the passes it signs (a pass is `name.expiry.signature`; the server keeps no list)."""

    def __init__(self, codes: dict[str, str] | None = None, secret: str = "", features: tuple[str, ...] = ()):
        self.gate = _voice.Gate(_Codes(dict(codes or {}), secret))   # type: ignore[arg-type]
        self.features = tuple(features)

    @classmethod
    def from_env(cls) -> "Experiments":
        try:
            codes = _voice.parse_codes(os.environ.get("EXPERIMENT_CODES", ""))
        except ValueError as e:
            raise ValueError(str(e).replace("VOICE_CODES", "EXPERIMENT_CODES")) from None
        # the decision model is offered only where the host has a chooser to ask
        features = (DECISION_MODEL,) if os.environ.get("INTENT_PROVIDER", "off") != "off" else ()
        return cls(codes, os.environ.get("EXPERIMENT_SECRET", ""), features)

    @property
    def enabled(self) -> bool:
        return bool(self.gate.config.codes)

    def person(self, headers: Any) -> str | None:
        """Whose pass a request carries, or None."""
        return self.gate.person(headers.get(HEADER))


def allowed() -> bool:
    """Whether the experimental features may run for the request being served: always on a host with no gate,
    and on a gated host only for a request that carries a valid pass."""
    return not _gated or _person.get() is not None


class _Pass:
    """ASGI middleware: reads the pass of each request once, so the code that serves it can ask `allowed()`."""

    def __init__(self, app: Any, experiments: Experiments):
        self.app, self.experiments = app, experiments

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        token = next((v.decode("latin-1") for k, v in scope.get("headers") or [] if k == HEADER.encode()), None)
        mark = _person.set(self.experiments.gate.person(token) if token else None)
        try:
            await self.app(scope, receive, send)
        finally:
            _person.reset(mark)


def install(app: Any, experiments: Experiments) -> None:
    """Gate this process: from now on `allowed()` is true only for a request with a valid pass."""
    global _gated
    _gated = True
    app.add_middleware(_Pass, experiments=experiments)


def uninstall() -> None:
    """For tests: the process is not gated any more."""
    global _gated
    _gated = False


class UnlockIn(BaseModel):
    code: str


def create_experiments_router(experiments: Experiments):
    """The routes of the gate. Mount them only when `experiments.enabled`."""
    if APIRouter is None:
        raise ImportError("the experiment routes need: pip install 'formguide[server]'")
    r = APIRouter()

    @r.get("")
    @r.get("/")
    def features(request: Request) -> dict:
        return {"features": list(experiments.features), "unlocked": experiments.person(request.headers) is not None}

    @r.post("/unlock")
    def unlock(body: UnlockIn, request: Request) -> dict:
        got = experiments.gate.unlock(body.code, request.client.host if request.client else "?")
        if not got:
            raise HTTPException(403, "That code does not open the experimental features.")
        return {"person": got[0], "pass": got[1], "features": list(experiments.features)}

    return r
