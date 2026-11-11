"""Optional HTTP layer: a FastAPI router over a FormGuide (needs fastapi + python-multipart).

    app.include_router(create_router(guide), prefix="/agent")

POST /layouts                        {jsx, form_id?, domain?}   register a form (once per JSX)
POST /run                            AG-UI RunAgentInput -> SSE  one chat turn / resume / tool results
POST /prefill                        {state, data?, text?, attachment_ids?, thread_id?}  values to prefill
POST /attachments                    multipart thread_id + file  a user document
GET  /kb/{form_id}                   documents in the form's scope + compiled knowledge
POST /kb/{namespace}/documents       multipart files            managers upload documents
DELETE /kb/{namespace}/documents/{doc_id}
POST /kb/{form_id}/compile           {jsx, config}              documents -> domain pack
GET  /threads/{thread_id}            transcript + pending card, to restore a conversation
                                     (?format=agui: AG-UI messages for agent.setMessages)
DELETE /threads/{thread_id}          forget a conversation (transcript + model history)
GET  /debug/{thread_id}              history as the model sees it (development)
"""
from __future__ import annotations

import json
from typing import Any

try:
    from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
    from fastapi.responses import StreamingResponse

    from . import agui
except ImportError as e:  # pragma: no cover
    raise ImportError(f"{e}: the HTTP layer needs: pip install 'formguide[server]'") from e
from pydantic import BaseModel, ValidationError

from .guide import FormGuide


class LayoutIn(BaseModel):
    jsx: str
    form_id: str | None = None
    domain: dict[str, Any] | None = None
    config: dict[str, Any] | None = None   # a sample {props, state}: adds value-format warnings


class PrefillIn(BaseModel):
    state: dict[str, Any]
    data: dict[str, Any] | None = None
    text: str | None = None
    attachment_ids: list[str] | None = None
    thread_id: str | None = None


class CompileIn(BaseModel):
    jsx: str
    config: dict[str, Any]


def create_router(guide: FormGuide, *, debug: bool = True) -> APIRouter:
    r = APIRouter()

    def bad(e: Exception) -> HTTPException:
        return HTTPException(400, str(e))

    @r.post("/layouts")
    def put_layout(body: LayoutIn) -> dict:
        return guide.register_form(body.jsx, body.form_id, body.domain, body.config)

    @r.get("/layouts/{h}")
    def has_layout(h: str) -> dict:
        if not guide.layout(h):
            raise HTTPException(404, "unknown layout")
        return {"jsx_hash": h}

    @r.post("/run")
    async def run(request: Request) -> StreamingResponse:
        try:
            kw = agui.run_kwargs(await request.json())
        except (ValidationError, ValueError) as e:
            raise HTTPException(422, f"not an AG-UI RunAgentInput: {e}") from None
        if kw["resume"] is None and not guide.layout(kw["state"].get("jsx_hash", "")):
            raise HTTPException(409, "unknown jsx_hash: POST /layouts first")
        enc = agui.encoder(request.headers.get("accept"))

        async def events():
            async for ev in guide.run(**kw):
                yield agui.encode(ev, enc)

        return StreamingResponse(events(), media_type=enc.get_content_type(),
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @r.post("/prefill")
    async def prefill(body: PrefillIn) -> dict:
        try:
            return await guide.suggest_prefill(body.state, data=body.data, text=body.text,
                                               attachment_ids=body.attachment_ids, thread_id=body.thread_id)
        except KeyError as e:
            raise HTTPException(409, str(e)) from None

    @r.post("/attachments")
    async def upload_attachment(thread_id: str = Form(...), file: UploadFile = File(...)) -> dict:
        try:
            return guide.save_attachment(thread_id, file.filename or "file", await file.read())
        except ValueError as e:
            raise bad(e) from None

    @r.get("/kb/{form_id}")
    def kb_get(form_id: str) -> dict:
        try:
            return {"documents": guide.knowledge.documents_for(form_id),
                    "namespaces": guide.knowledge.namespaces_for(form_id),
                    "compiled": guide.knowledge.compiled(form_id)}
        except ValueError as e:
            raise bad(e) from None

    @r.post("/kb/{namespace}/documents")
    async def kb_upload(namespace: str, files: list[UploadFile] = File(...)) -> dict:
        try:
            added = [guide.add_document(namespace, f.filename or "document", await f.read()) for f in files]
            return {"added": added, "documents": guide.knowledge.list_documents(namespace)}
        except ValueError as e:
            raise bad(e) from None

    @r.delete("/kb/{namespace}/documents/{doc_id}")
    def kb_delete(namespace: str, doc_id: str) -> dict:
        try:
            if not guide.delete_document(namespace, doc_id):
                raise HTTPException(404, "unknown document")
            return {"documents": guide.knowledge.list_documents(namespace)}
        except ValueError as e:
            raise bad(e) from None

    @r.post("/kb/{form_id}/compile")
    async def kb_compile(form_id: str, body: CompileIn) -> dict:
        try:
            return await guide.compile_knowledge(form_id, body.jsx, body.config)
        except (ValueError, RuntimeError) as e:
            raise bad(e) from None

    @r.get("/threads/{thread_id}")
    def get_thread(thread_id: str, format: str | None = None, form_id: str | None = None) -> dict:  # noqa: A002
        """`form_id`: for an empty thread, also return that form's `starters` (opening messages)."""
        try:
            t = guide.thread(thread_id, form_id)
            if format == "agui":
                return {"thread_id": thread_id, "messages": guide.thread_messages(thread_id),
                        "pending_card": t["pending_card"], **({"starters": t["starters"]} if "starters" in t else {})}
            return t
        except ValueError as e:
            raise bad(e) from None

    @r.delete("/threads/{thread_id}")
    async def delete_thread(thread_id: str) -> dict:
        try:
            await guide.delete_thread(thread_id)
        except ValueError as e:
            raise bad(e) from None
        return {"deleted": thread_id}

    if debug:
        @r.get("/debug/{thread_id}")
        async def debug_thread(thread_id: str) -> dict:
            return {"messages": await guide.history(thread_id), "runs": guide.recent_runs(thread_id)}

    return r
