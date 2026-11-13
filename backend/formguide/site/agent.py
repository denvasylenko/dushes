"""The site agent: answers from the site's content and moves the user around the site.

Tools:
  search_site(query)                 more passages when the first ones do not answer
  ask_documents(question)            the document researcher over the site's business documents (when it has any)
  navigate(path, tab?, section?)     open a page (and a tab, accordion or section on it)
  open_form(form_id, note)           open the page with that form and hand the request to the form agent

`navigate` and `open_form` are checked against the site map. A valid call becomes a
CUSTOM `site_directive {type: "navigate", path, tab?, section?, form_id?}` for the page.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from .sitemap import SiteMap

log = logging.getLogger("formguide.site")
MAX_ROUNDS = 4

SYSTEM = """You are the assistant of the site "{title}". You help people find things on the site and get things done.
- Answer in one to three short sentences. Facts about this business (its products, prices, rules, partners, opening hours) come only from the site's passages, the document passages and ask_documents; name the page or document you used. Never invent such facts: if none of them answers, say so and offer the closest page.
- General concepts that are not about this business (what a co-borrower is, what an independent valuation means) you may explain from general knowledge, briefly, and say it is general: the business's own terms may differ.
- For a question about a term, a partner, a condition or a policy that the passages below do not settle, call ask_documents before answering.
- When the user wants to go somewhere or would be helped by seeing a page, call navigate (a page path from the site contents, plus a tab, accordion or section id on it when that is where the answer is).
- When the user wants to do something a form on the site does (apply, book), call open_form with that form and a note: one or two sentences of everything the user already said that the form needs (amounts, dates, names, choices), in their words. Do not ask for those details yourself: the form's own assistant takes over on that page.
- Never invent pages, tabs or forms: use only what the site contents list.
- Reply in the user's language. Call tools without announcing them.

Site contents (path | title | description | form | tabs, accordions, sections):
{contents}

The user is on: {page}

Site passages:
{passages}

Document passages:
{doc_passages}"""

TOOLS: list[dict[str, Any]] = [
    {"name": "search_site", "description": "Search the site's pages again with other words.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "navigate", "description": "Open a page of the site, optionally a tab, accordion or section on it.",
     "parameters": {"type": "object", "properties": {
         "path": {"type": "string", "description": "a page path from the site contents, e.g. /loans"},
         "tab": {"type": "string", "description": "a tab or accordion id on that page"},
         "section": {"type": "string", "description": "a section id on that page"}},
         "required": ["path"]}},
    {"name": "ask_documents", "description": "Ask the document researcher a question about the business's documents "
                                      "(terms, partners, conditions, policies). Returns a short answer with sources.",
     "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}},
    {"name": "open_form", "description": "Open the page with this form and hand the request to the form's assistant.",
     "parameters": {"type": "object", "properties": {
         "form_id": {"type": "string"},
         "note": {"type": "string", "description": "what the user already said that the form needs"}},
         "required": ["form_id", "note"]}},
]


def passages(site: SiteMap, chunks: list) -> str:
    return "\n\n".join(f"<passage page=\"{c.doc_id}\" title=\"{c.title} / {c.section}\">\n{c.text}\n</passage>"
                       for c in chunks) or "(no passage matched)"


def directive(site: SiteMap, args: dict[str, Any]) -> tuple[str, dict | None]:
    """navigate -> (what the model is told, the directive or None)."""
    page = site.page(str(args.get("path") or ""))
    if not page:
        return f"There is no page {args.get('path')!r}. Use a path from the site contents.", None
    d: dict[str, Any] = {"type": "navigate", "path": page.path}
    for key in ("tab", "section"):
        pid = str(args.get(key) or "").strip()
        if not pid:
            continue
        part = page.part(pid)
        if not part:
            return f"The page {page.path} has no {key} {pid!r}.", None
        d["tab" if part.kind in ("tab", "accordion") else "section"] = part.id
    return f"Opened {page.title}.", d


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type", "text") == "text")
    return str(content or "")


async def answer(model: BaseChatModel, site: SiteMap, question: str, history: list[tuple[str, str]], page_path: str,
                 thread_id: str, run_id: str, on_handoff: Callable[[str, str], None], doc_passages: str = "",
                 ask_docs: Callable[[str], Awaitable[str]] | None = None) -> AsyncIterator[dict]:
    """One site turn as AG-UI events. `on_handoff(form_id, note)` keeps the note for the form page's first run;
    `doc_passages` are the business documents that match the question, `ask_docs` the document researcher."""
    yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
    found = site.search(question, k=5)
    seen = {c.id for c in found}
    here = site.page(page_path)
    system = SYSTEM.format(title=site.title, contents=site.contents(), passages=passages(site, found),
                           doc_passages=doc_passages or "(none matched)",
                           page=f"{here.path} ({here.title})" if here else page_path or "/")
    msgs: list[Any] = [SystemMessage(system)]
    for role, text in history:
        msgs.append(HumanMessage(text) if role == "user" else AIMessage(text))
    msgs.append(HumanMessage(question))
    tools = TOOLS if ask_docs else [t for t in TOOLS if t["name"] != "ask_documents"]
    try:
        bound = model.bind_tools(tools)
    except NotImplementedError:
        bound = model
    mid = f"msg_{uuid.uuid4().hex[:12]}"
    started = False
    directives: list[dict] = []
    try:
        for _ in range(MAX_ROUNDS):
            full: AIMessageChunk | None = None
            async for chunk in bound.astream(msgs):
                full = chunk if full is None else full + chunk
                delta = _text(chunk.content)
                if delta:
                    if not started:
                        yield {"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"}
                        started = True
                    yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": delta}
            calls = list(getattr(full, "tool_calls", None) or [])
            if not calls:
                break
            if started:   # the text before the tools is its own message; the next round starts a new one
                yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
                mid, started = f"msg_{uuid.uuid4().hex[:12]}", False
            msgs.append(AIMessage(content=full.content if full else "", tool_calls=calls))
            for tc in calls:
                name, args, cid = tc.get("name", ""), tc.get("args") or {}, tc.get("id") or f"call_{uuid.uuid4().hex[:12]}"
                yield {"type": "TOOL_CALL_START", "toolCallId": cid, "toolCallName": name}
                yield {"type": "TOOL_CALL_ARGS", "toolCallId": cid, "delta": json.dumps(args, ensure_ascii=False)}
                yield {"type": "TOOL_CALL_END", "toolCallId": cid}
                if name == "search_site":
                    more = [c for c in site.search(str(args.get("query") or ""), k=4) if c.id not in seen]
                    seen.update(c.id for c in more)
                    result = passages(site, more) if more else "Nothing more found."
                elif name == "navigate":
                    result, d = directive(site, args)
                    if d:
                        directives.append(d)
                elif name == "ask_documents" and ask_docs:
                    try:
                        result = await ask_docs(str(args.get("question") or question))
                    except Exception as e:  # noqa: BLE001 — a failed lookup must not break the turn
                        result = f"The document lookup failed ({type(e).__name__}); answer from the passages or say you do not know."
                elif name == "open_form":
                    page = site.form_page(str(args.get("form_id") or ""))
                    if not page:
                        result = f"There is no form {args.get('form_id')!r} on the site."
                    else:
                        on_handoff(page.form or "", str(args.get("note") or "").strip()[:600])
                        directives.append({"type": "navigate", "path": page.path, "form_id": page.form})
                        result = f"Opened {page.title}; the form's assistant takes over there. Say so in one short sentence."
                else:
                    result = f"Unknown tool {name}."
                msgs.append(ToolMessage(content=result, tool_call_id=cid))
                yield {"type": "TOOL_CALL_RESULT", "toolCallId": cid, "messageId": f"tool_{uuid.uuid4().hex[:12]}",
                       "content": result[:200], "role": "tool"}
    except Exception as e:  # noqa: BLE001 — a human error, never a stack trace
        log.exception("site answer failed")
        if started:
            yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
        yield {"type": "RUN_ERROR", "message": f"The assistant is unavailable right now ({type(e).__name__})."}
        return
    if started:
        yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
    if directives:   # the last move wins: one page at a time
        yield {"type": "CUSTOM", "name": "site_directive", "value": directives[-1]}
    yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}
