"""Optional HTTP layer: a FastAPI router over a FormGuide (needs fastapi + python-multipart).

    app.include_router(create_router(guide), prefix="/agent")

POST /layouts                        {jsx, form_id?, domain?}   register a form (once per JSX)
POST /run                            AG-UI RunAgentInput -> SSE  one chat turn / resume
POST /attachments                    multipart thread_id + file  a user document
GET  /kb/{form_id}                   documents in the form's scope + compiled knowledge
POST /kb/{namespace}/documents       multipart files            managers upload documents
DELETE /kb/{namespace}/documents/{doc_id}
POST /kb/{form_id}/compile           {jsx, config}              documents -> domain pack
GET  /debug/{thread_id}              history as the model sees it (development)
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .guide import FormGuide


class LayoutIn(BaseModel):
    jsx: str
    form_id: str | None = None
    domain: dict[str, Any] | None = None


class RunIn(BaseModel):
    """Same shape as AG-UI RunAgentInput (what CopilotKit / HttpAgent sends)."""
    threadId: str
    runId: str | None = None
    messages: list[dict] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    forwardedProps: dict[str, Any] = Field(default_factory=dict)


class CompileIn(BaseModel):
    jsx: str
    config: dict[str, Any]


def create_router(guide: FormGuide, *, debug: bool = True) -> APIRouter:
    r = APIRouter()

    def bad(e: Exception) -> HTTPException:
        return HTTPException(400, str(e))

    @r.post("/layouts")
    def put_layout(body: LayoutIn) -> dict:
        return guide.register_form(body.jsx, body.form_id, body.domain)

    @r.get("/layouts/{h}")
    def has_layout(h: str) -> dict:
        if not guide.layout(h):
            raise HTTPException(404, "unknown layout")
        return {"jsx_hash": h}

    @r.post("/run")
    async def run(body: RunIn) -> StreamingResponse:
        resume = (body.forwardedProps.get("command") or {}).get("resume")
        if resume is None and not guide.layout(body.state.get("jsx_hash", "")):
            raise HTTPException(409, "unknown jsx_hash: POST /layouts first")
        user = next((m for m in reversed(body.messages) if m.get("role") == "user"), {})

        async def events():
            async for ev in guide.run(body.threadId, message=user.get("content", ""), state=body.state,
                                      resume=resume, run_id=body.runId):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

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

    if debug:
        @r.get("/debug/{thread_id}")
        def debug_thread(thread_id: str) -> dict:
            return {"messages": guide.history(thread_id)}

    return r
