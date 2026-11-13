"""SiteGuide: one assistant for a whole site, above the form agent.

    site = SiteGuide(form_guide, SiteMap.load("site.yaml"))
    async for ev in site.run(thread_id, message="open the contacts page", state={"page": {"path": "/apply"}, "form": {...}}):
        ...

Each turn goes to one of two agents:
- the form agent: `FormGuide.run`, unchanged, on a page with a form (its own conversation per form, thread
  `<site thread>-<form id>`), and for every card answer;
- the site agent (agent.py): on pages without a form, and on a form page when the message is about the
  site rather than the form (navigation, another page).

A hand-off: the site agent's open_form keeps a note of what the user wants; the next run on the form page
with `forwardedProps.handoff` gives the form agent that note as its first message.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ..transcript import check_thread_id, new_entry

try:   # module level: the router's annotations are resolved here (postponed annotations)
    from fastapi import Request
    from fastapi.responses import StreamingResponse
except ImportError:  # pragma: no cover - the HTTP layer is optional
    Request = StreamingResponse = Any  # type: ignore[assignment,misc]
from . import agent
from .sitemap import SiteMap

if TYPE_CHECKING:
    from ..guide import FormGuide

# a message that is about moving around the site, not about the form on the page
_NAV = re.compile(r"\b(go to|go back to|take me|open|show me the|navigate|switch to|back to|where (is|can i find)|"
                  r"which page|another page|home ?page|main page)\b", re.I)
HISTORY = 6


class SiteGuide:
    def __init__(self, form_guide: FormGuide, site: SiteMap, model: Any = None):
        self.forms = form_guide
        self.site = site
        self.model = model   # the site agent's model; default: the form guide's agent model
        self._handoff: dict[str, dict[str, str]] = {}   # site thread -> {form_id, note}

    # ------------------------------------------------------------ routing
    def route(self, message: str | None, state: dict[str, Any], resume: Any = None, handoff: bool = False) -> str:
        """'form' or 'site' for this turn."""
        form = state.get("form") or None
        if resume is not None:
            return "form" if form else "site"
        if not form:
            return "site"
        if handoff or not message:
            return "form"
        return "site" if self._about_site(message, state) else "form"

    def _about_site(self, message: str, state: dict[str, Any]) -> bool:
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        text = message.lower()
        if _NAV.search(text):
            return True
        own = set(here.keywords) | {here.title.lower()} if here else set()   # the form page's own words stay with the form
        for p in self.site.pages:   # another page named by its title or keywords
            if here and p.path == here.path:
                continue
            words = [w for w in (p.title.lower(), *p.keywords) if w not in own]
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words if len(w) > 2):
                return True
        return False

    # ------------------------------------------------------------ a turn
    async def run(self, thread_id: str, *, message: str | None = None, state: dict[str, Any] | None = None,
                  resume: dict[str, Any] | None = None, run_id: str | None = None, handoff: bool = False,
                  **form_kwargs: Any) -> AsyncIterator[dict]:
        check_thread_id(thread_id)
        state = state or {}
        run_id = run_id or str(uuid.uuid4())
        mode = self.route(message, state, resume, handoff)
        if mode == "form":
            form = state["form"]
            fid = str(form.get("form_id") or "form")
            kw: dict[str, Any] = dict(form_kwargs)
            note = self._handoff.pop(thread_id, None) if handoff else None
            if note and note.get("form_id") == fid and note.get("note") and not message:
                # the request the user made elsewhere on the site, as the form agent's first message: it then
                # proposes what the note covers with its usual tools and cards
                message = f"[Handed over by the site assistant] On the site the user said: {note['note']}"
            async for ev in self.forms.run(f"{thread_id}-{fid}"[:100], message=message, state=form, resume=resume,
                                           run_id=run_id, **kw):
                yield ev
            return
        tx = self.forms.transcripts
        history = [(e["kind"], e.get("text", "")) for e in tx.list(thread_id) if e["kind"] in ("user", "assistant")][-HISTORY:]
        if message:
            tx.append(thread_id, new_entry("user", text=message))
        said: list[str] = []

        def keep(form_id: str, note: str) -> None:
            self._handoff[thread_id] = {"form_id": form_id, "note": note}

        page = ((state.get("page") or {}).get("path")) or "/"
        async for ev in agent.answer(self.model or self.forms.models.agent, self.site, message or "", history, page,
                                     thread_id, run_id, keep):
            if ev["type"] == "TEXT_MESSAGE_CONTENT":
                said.append(ev["delta"])
            yield ev
        if said:
            tx.append(thread_id, new_entry("assistant", text="".join(said)))


def create_site_router(site: SiteGuide):
    """FastAPI router: POST /run (AG-UI RunAgentInput; state {page, form?}), GET /map (the site map for the page)."""
    from fastapi import APIRouter, HTTPException
    from pydantic import ValidationError

    from .. import agui

    r = APIRouter()

    @r.get("/map")
    def site_map() -> dict:
        return site.site.as_dict()

    @r.post("/run")
    async def run(request: Request) -> StreamingResponse:
        body = await request.json()
        try:
            kw = agui.run_kwargs(body)
        except (ValidationError, ValueError) as e:
            raise HTTPException(422, f"not an AG-UI RunAgentInput: {e}") from None
        fwd = body.get("forwardedProps") if isinstance(body.get("forwardedProps"), dict) else {}
        kw["handoff"] = bool(fwd.get("handoff"))
        state = kw.get("state") or {}
        form = state.get("form") if isinstance(state.get("form"), dict) else None
        if form and kw["resume"] is None and not site.forms.layout(form.get("jsx_hash", "")):
            raise HTTPException(409, "unknown jsx_hash: POST /layouts first")
        enc = agui.encoder(request.headers.get("accept"))

        async def events():
            async for ev in site.run(**kw):
                yield agui.encode(ev, enc)

        return StreamingResponse(events(), media_type=enc.get_content_type(),
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return r
