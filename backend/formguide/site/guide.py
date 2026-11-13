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

Knowledge: the site agent reads the site map and the business documents of the site's own namespaces
(`knowledge_namespaces`, default: "site" plus every form on the map), through a search and the document
researcher. The form agent keeps its own form's documents.

One conversation: the site thread's transcript holds every turn the user saw, the site agent's and the
form agents' (their text; their cards stay in the form's own thread), plus the hand-off note, so the chat
and the note survive a reload or a restart. `GET /threads/{id}` returns it for the page.
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
SCOPE = "site"   # the knowledge scope of the site agent
_NAV = re.compile(r"\b(go to|go back to|take me|open (the|my|a|an|up)|show me the|navigate|switch to|back to|where (is|can i find)|"
                  r"which page|another page|home ?page|main page)\b", re.I)
HISTORY = 6


class SiteGuide:
    def __init__(self, form_guide: FormGuide, site: SiteMap, model: Any = None,
                 knowledge_namespaces: list[str] | None = None, router_model: Any = None):
        self.forms = form_guide
        self.site = site
        self.model = model   # the site agent's model; default: the form guide's agent model
        self.router_model = router_model or form_guide.models.memory   # a cheap model for unclear messages
        # the site's documents: the "site" namespace and the forms' own, seen through one knowledge scope
        spaces = knowledge_namespaces or ["site", *dict.fromkeys(p.form for p in site.pages if p.form)]
        self.forms.knowledge.scopes.setdefault(SCOPE, list(spaces))

    # ------------------------------------------------------------ the site's documents
    def doc_passages(self, question: str, k: int = 3) -> str:
        kb = self.forms.knowledge
        hits = kb.search(SCOPE, question, k=k) if kb.documents_for(SCOPE) else []
        return "\n\n".join(f"<document title=\"{c.title} / {c.section}\">\n{c.text}\n</document>" for _s, c in hits)

    async def ask_documents(self, question: str) -> str:
        from ..knowledge import research   # needs the `research` extra (deepagents)

        return await research.ask_documents(self.forms.knowledge, SCOPE, self.site.title, question,
                                            self.forms.models.research)

    # ------------------------------------------------------------ the hand-off note, kept in the transcript
    def _keep_note(self, thread_id: str, form_id: str, note: str) -> None:
        self.forms.transcripts.append(thread_id, new_entry("handoff", form_id=form_id, note=note, status="pending"))

    def _take_note(self, thread_id: str, form_id: str) -> str | None:
        tx = self.forms.transcripts
        e = next((x for x in reversed(tx.list(thread_id)) if x["kind"] == "handoff" and x.get("status") == "pending"), None)
        if not e:
            return None
        tx.update(thread_id, e["id"], status="used")
        return e.get("note") if e.get("form_id") == form_id else None

    # ------------------------------------------------------------ routing
    def route(self, message: str | None, state: dict[str, Any], resume: Any = None, handoff: bool = False) -> str:
        """'form', 'site', or 'unclear' (a form page and a message that names another page's words, without
        asking to go anywhere: a cheap model decides, see classify)."""
        form = state.get("form") or None
        if resume is not None:
            return "form" if form else "site"
        if not form:
            return "site"
        if handoff or not message:
            return "form"
        return self._about_site(message, state)

    def _about_site(self, message: str, state: dict[str, Any]) -> str:
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        text = message.lower()
        if _NAV.search(text):
            return "site"   # an explicit move: go to, open, take me ...
        own = set(here.keywords) | {here.title.lower()} if here else set()   # the form page's own words stay with the form
        for p in self.site.pages:   # another page named by its title or keywords
            if here and p.path == here.path:
                continue
            words = [w for w in (p.title.lower(), *p.keywords) if w not in own]
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words if len(w) > 2):
                return "unclear"   # "a car loan" on the loan form is the form's; "the barbershop prices" is not
        return "form"

    async def classify(self, message: str, state: dict[str, Any]) -> str:
        """One word from a cheap model for an unclear message on a form page; 'form' when it cannot tell."""
        import asyncio

        from langchain_core.messages import HumanMessage

        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        form = (state.get("form") or {}).get("form_id") or (here.form if here else "")
        prompt = (f"A user of the site \"{self.site.title}\" is on the page \"{here.title if here else '?'}\", which "
                  f"holds the form \"{form}\". They wrote: \"{message[:500]}\"\n"
                  "Answer with one word. form: it is about filling in or understanding this form (its fields, choices, "
                  "values, what it needs). site: it asks about something else on the site (another page, service, "
                  "opening hours, prices of something the form is not for).")
        try:
            out = await asyncio.wait_for(self.router_model.ainvoke([HumanMessage(prompt)]), timeout=4)
        except Exception:  # noqa: BLE001 — never block a turn on the router
            return "form"
        word = str(getattr(out, "content", out)).strip().lower()
        return "site" if word.startswith("site") else "form"

    def _carry_files(self, site_thread: str, form_thread: str, form: dict[str, Any], resume: Any) -> None:
        """The chat uploads under the site's conversation; the form agent reads files from its own."""
        ids = [str(a.get("id")) for a in form.get("attachments") or [] if isinstance(a, dict) and a.get("id")]
        if isinstance(resume, dict) and isinstance(resume.get("attachment_ids"), list):
            ids += [str(i) for i in resume["attachment_ids"]]
        for att_id in dict.fromkeys(ids):
            self.forms.attachments.copy(site_thread, form_thread, att_id)

    # ------------------------------------------------------------ the conversation for the page
    def thread(self, thread_id: str, form_id: str | None = None) -> dict[str, Any]:
        """{messages, pending_card}: every turn the user saw (AG-UI messages) and the open card of the form on
        the current page, if any."""
        check_thread_id(thread_id)
        msgs = [{"id": e["id"], "role": e["kind"], "content": e.get("text", "")}
                for e in self.forms.transcripts.list(thread_id) if e["kind"] in ("user", "assistant") and e.get("text")]
        pending = None
        if form_id:
            pending = self.forms.thread(f"{thread_id}-{form_id}"[:100]).get("pending_card")
        return {"thread_id": thread_id, "messages": msgs, "pending_card": pending}

    # ------------------------------------------------------------ a turn
    async def run(self, thread_id: str, *, message: str | None = None, state: dict[str, Any] | None = None,
                  resume: dict[str, Any] | None = None, run_id: str | None = None, handoff: bool = False,
                  **form_kwargs: Any) -> AsyncIterator[dict]:
        check_thread_id(thread_id)
        state = state or {}
        run_id = run_id or str(uuid.uuid4())
        mode = self.route(message, state, resume, handoff)
        if mode == "unclear":
            mode = await self.classify(message or "", state)
        if mode == "form":
            form = state["form"]
            fid = str(form.get("form_id") or "form")
            kw: dict[str, Any] = dict(form_kwargs)
            note = self._take_note(thread_id, fid) if handoff and not message else None
            typed = message
            if note:
                # the request the user made elsewhere on the site, as the form agent's first message: it then
                # proposes what the note covers with its usual tools and cards
                message = f"[Handed over by the site assistant] On the site the user said: {note}"
            form_thread = f"{thread_id}-{fid}"[:100]
            self._carry_files(thread_id, form_thread, form, resume)
            tx = self.forms.transcripts
            if typed:
                tx.append(thread_id, new_entry("user", text=typed, form_id=fid))
            said: list[str] = []
            async for ev in self.forms.run(form_thread, message=message, state=form, resume=resume,
                                           run_id=run_id, **kw):
                if ev["type"] == "TEXT_MESSAGE_CONTENT":
                    said.append(ev["delta"])
                yield ev
            if "".join(said).strip():
                tx.append(thread_id, new_entry("assistant", text="".join(said), form_id=fid))
            return
        tx = self.forms.transcripts
        history = [(e["kind"], e.get("text", "")) for e in tx.list(thread_id) if e["kind"] in ("user", "assistant")][-HISTORY:]
        if message:
            tx.append(thread_id, new_entry("user", text=message))
        said: list[str] = []

        def keep(form_id: str, note: str) -> None:
            self._keep_note(thread_id, form_id, note)

        page = ((state.get("page") or {}).get("path")) or "/"
        has_docs = bool(self.forms.knowledge.documents_for(SCOPE))
        async for ev in agent.answer(self.model or self.forms.models.agent, self.site, message or "", history, page,
                                     thread_id, run_id, keep, doc_passages=self.doc_passages(message or "") if has_docs else "",
                                     ask_docs=self.ask_documents if has_docs else None):
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

    @r.get("/threads/{thread_id}")
    def thread(thread_id: str, form_id: str | None = None) -> dict:
        """The site chat for the page after a reload: its messages and, on a form page, the form's open card."""
        try:
            return site.thread(thread_id, form_id)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None

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
