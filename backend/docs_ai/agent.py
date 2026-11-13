"""The docs assistant's turn: a small tool-using agent whose tools put cards in the chat.

The model answers in one or two sentences and calls tools for everything else:

  show_code(blocks)          code cards, the blocks quoted verbatim from the docs (ids from the passages)
  show_pages(urls)           page cards: where it is documented
  show_steps(steps)          a numbered how-to, each step with an optional code block
  show_card(specimen)        a live card from the card gallery
  suggest_next(questions)    two or three follow-up questions, shown as chips
  search_docs(query)         a second lookup when the first passages do not cover the question

Cards are collected during the rounds and sent after the text (`CUSTOM docs_card`), follow-ups last
(`CUSTOM suggestions`), the way Herefront's chat orders them: read, then tap.
"""
from __future__ import annotations

import json
import re
import logging
import uuid
from typing import Any, AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from . import recipes
from .corpus import Corpus

RECIPES = recipes.load()

log = logging.getLogger("formguide.docs_ai")

MAX_ROUNDS = 4

# a question about the whole configuration (every key, all options, the full file)
WHOLE_CONFIG = re.compile(r"(?i)\b(whole|full|complete|entire|every|all)\b.{0,40}\b(config|configuration|keys|options|settings|yaml)\b"
                          r"|\b(config|configuration)\b.{0,30}\b(whole|full|complete|entire|every key|all keys)\b")

# The card gallery's specimens (site/src/demo/gallery.ts): id -> what it shows.
SPECIMENS = {
    "set-fields": "field changes: values with reasons, one Fill in button, Undo",
    "document": "values read from a scanned document, with a value to check",
    "consent": "consents, never pre-ticked",
    "chips": "a question with a few options as chips that fill the field",
    "yesno": "a yes / no question for a checkbox field",
    "details": "options with a line of description",
    "compare": "a comparison table of options with a recommended one",
    "search": "a long list with search",
    "multi": "several answers at once",
    "several": "two or three short fields in one card",
    "date-ahead": "a date ahead: quick picks and a calendar",
    "date-past": "a date in the past: the calendar with years and months",
    "time": "time slots",
    "stepper": "a short number range as a stepper with a live preview",
    "slider": "a long number range as a slider",
    "address": "an address with suggestions",
    "upload": "a document request with a drop zone",
    "status": "what is left, by section",
    "review": "the check before sending: errors with fixes, warnings",
    "confirm": "a confirmation that becomes a receipt",
    "sources": "source chips under an answer",
    "suggestions": "quick replies and action chips",
}

SYSTEM = """You are Ask AI, the assistant of the Dushes documentation. Dushes is an AI assistant for a product's interface: \
it answers from the site's pages and documents, takes people to the right page, tab or field, and fills forms with them \
after they confirm. It has two modes: the site assistant (a whole site or app) and the form assistant (a large form). \
A Python backend on LangGraph with any LangChain model (the Python package and its code names are `formguide`), AG-UI \
on the wire, and the <agui-chat> Web Component in the browser. Call the product Dushes; keep code names as they are.

How you answer:
- Write one or two short sentences of plain text: the answer itself. No headings, no code in the text, no lists of \
links, no "Sources:" line.
- Put everything else in cards, by calling tools: show_code ONCE for code (pick the one block that answers best from \
the passages; add a second or third id only when it is the same thing in another form, e.g. YAML and Python, which \
become tabs; when the question names a language or stack, Python or the browser, pick that one first), show_steps for a how-to with more than one \
step, show_pages for where it is documented (always, 1-3 pages you used), show_card when the question is about what a \
card looks like.
- Asked for the whole configuration, every key or all options: search_docs "Every key in one file" if needed, then \
one show_code with BOTH blocks of that section, the YAML block first and the Python block second (they become tabs; \
this is the one exception to a single block). Never answer it with a page link only.
- Always finish with suggest_next: 2-3 short follow-up questions the reader is likely to ask next, in their language.
- Use only the passages, the table of contents and what search_docs returns. If they do not answer the question, \
say so in one sentence, call search_docs once with other words, and if still nothing, show the closest page.
- Never invent keys, options, endpoints or functions. Code goes only through show_code, never typed by you.
- Answer in the language of the question. Call tools without announcing them.

Gallery cards for show_card:
{specimens}

Table of contents:
{toc}

Documentation passages (code blocks are marked [code <id> · <language> · <label>]):
{passages}"""

TOOLS: list[dict[str, Any]] = [
    {"name": "show_code", "description": "Show code from the docs as a card. Several blocks become tabs.",
     "parameters": {"type": "object", "properties": {
         "blocks": {"type": "array", "items": {"type": "string"}, "description": "block ids such as b12, at most 4"},
         "caption": {"type": "string", "description": "a few words above the code, optional"}},
         "required": ["blocks"]}},
    {"name": "show_pages", "description": "Show 1-3 documentation pages as cards (where it is documented).",
     "parameters": {"type": "object", "properties": {
         "urls": {"type": "array", "items": {"type": "string"}, "description": "page or section addresses"}},
         "required": ["urls"]}},
    {"name": "show_steps", "description": "Show a numbered how-to. Each step is a short sentence, optionally with one code block.",
     "parameters": {"type": "object", "properties": {
         "title": {"type": "string"},
         "steps": {"type": "array", "items": {"type": "object", "properties": {
             "text": {"type": "string"}, "block": {"type": "string", "description": "a block id, optional"}},
             "required": ["text"]}}},
         "required": ["steps"]}},
    {"name": "show_card", "description": "Show a live card from the card gallery.",
     "parameters": {"type": "object", "properties": {"specimen": {"type": "string", "enum": list(SPECIMENS)}},
                    "required": ["specimen"]}},
    {"name": "suggest_next", "description": "2-3 follow-up questions as chips. Call it last, every time.",
     "parameters": {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "string"}}},
                    "required": ["questions"]}},
    {"name": "search_docs", "description": "Search the docs again with other words.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]

LABELS = {"search_docs": "Searching the docs"}


def passages(chunks: list) -> str:
    return "\n\n".join(f"<passage title=\"{c.title} / {c.section}\" address=\"{c.doc_id}\">\n{c.text}\n</passage>" for c in chunks)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) and p.get("type", "text") == "text" else "" for p in content)
    return str(content or "")


def _block(corpus: Corpus, bid: str) -> dict[str, Any] | None:
    b = corpus.blocks.get(str(bid).strip())
    return b and {"id": b.id, "lang": b.lang, "label": b.label, "code": b.code, "url": b.url, "page": b.page, "section": b.section}


def _page(corpus: Corpus, url: str) -> dict[str, Any] | None:
    url = str(url).strip()
    base, _, anchor = url.partition("#")
    known = corpus.pages_by_url.get(base) or corpus.pages_by_url.get(base.rstrip("/") + "/")
    if not known:
        return None
    title, desc = known
    section = corpus.section_of.get(url, "") if anchor else ""
    return {"url": url, "title": title, "group": _group(base), "section": section if section != title else "",
            "description": desc}


# the site's sidebar groups, by the first part of a page's path: "Reference · Configuration" vs "Backend · Configuration"
GROUPS = {"getting-started": "Get started", "backend": "Backend", "frontend": "Frontend", "form": "Your form",
          "built-on": "Built on", "concepts": "Concepts", "reference": "Reference", "specifications": "Specifications"}


def _group(url: str) -> str:
    for part in url.split("/"):
        if part in GROUPS:
            return GROUPS[part]
    return ""


# ---------------------------------------------------------------- the cards a reader sees

MAX_CARDS = 3
MAX_TABS = 3
_PY = re.compile(r"\b(p[yt]?th?on|py|fastapi|yaml|yml|backend|server|uvicorn|langgraph|pip|uv)\b", re.I)
_WEB = re.compile(r"\b(react|tsx|jsx|javascript|js|typescript|ts|browser|frontend|html|widget|vue|angular|npm)\b", re.I)
SERVER_LANGS = {"yaml", "yml", "python", "py", "bash", "sh", "toml", "json"}
WEB_LANGS = {"tsx", "ts", "jsx", "js", "javascript", "typescript", "html", "vue"}


def asked_stack(question: str) -> str:
    """'server' or 'web' when the question names one (typos included), else ''."""
    py, web = bool(_PY.search(question)), bool(_WEB.search(question))
    return "server" if py and not web else "web" if web and not py else ""


def _norm_code(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


def compose(cards: list[dict[str, Any]], question: str = "") -> list[dict[str, Any]]:
    """The model may call show_code several times: one reader-sized answer comes out of it.
    - code: one card, its blocks deduplicated (by id and by identical code), the asked stack first, at most
      MAX_TABS tabs; blocks a steps card already shows are dropped;
    - pages: one card, without the pages the code cards already name as their source, at most 2;
    - at most MAX_CARDS cards: code / steps first, then a live card, then pages."""
    stack = asked_stack(question)
    pref = SERVER_LANGS if stack == "server" else WEB_LANGS if stack == "web" else set()
    steps = [c for c in cards if c["kind"] == "steps"][:1]
    in_steps = {_norm_code(s["block"]["code"]) for c in steps for s in c["steps"] if s.get("block")}
    code_cards = [c for c in cards if c["kind"] == "code"]
    if pref:   # the card that answers the asked stack leads
        code_cards.sort(key=lambda c: not any(b["lang"].lower() in pref for b in c["blocks"]))
    blocks: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_code = set(in_steps)
    lead_section = None
    for c in code_cards:
        for b in c["blocks"]:
            key = _norm_code(b["code"])
            if b["id"] in seen_ids or key in seen_code:
                continue
            section = (b.get("page"), b.get("section"))
            if lead_section is None:
                lead_section = section
            elif section != lead_section:   # another topic: one answer, one card
                continue
            seen_ids.add(b["id"])
            seen_code.add(key)
            blocks.append(b)
    if pref:
        blocks.sort(key=lambda b: b["lang"].lower() not in pref)
    out: list[dict[str, Any]] = [*steps]
    if blocks:
        out.append({"kind": "code", "caption": code_cards[0].get("caption", "") if code_cards else "",
                    "blocks": blocks[:MAX_TABS]})
    out += [c for c in cards if c["kind"] == "live"][:1]
    sources = {(b.get("url") or "").split("#")[0].rstrip("/") for b in blocks[:MAX_TABS]}
    sources |= {(s["block"].get("url") or "").split("#")[0].rstrip("/") for c in steps for s in c["steps"] if s.get("block")}
    pages: list[dict[str, Any]] = []
    for c in cards:
        if c["kind"] != "pages":
            continue
        for p in c["pages"]:
            base = p["url"].split("#")[0].rstrip("/")
            if base in sources or any(q["url"] == p["url"] for q in pages):
                continue
            pages.append(p)
    if pages:
        out.append({"kind": "pages", "pages": pages[:2]})
    return out[:MAX_CARDS]


def whole_config_card(corpus: Corpus) -> dict[str, Any] | None:
    """The configuration guide's one-file section as a code card: the YAML first, then the same in Python."""
    blocks = [b for b in corpus.blocks.values() if b.section == "Every key in one file"]
    blocks.sort(key=lambda b: b.lang != "yaml")
    picked = [x for x in (_block(corpus, b.id) for b in blocks[:2]) if x]
    return {"kind": "code", "caption": "Every key, with its default", "blocks": picked} if picked else None


def run_tool(name: str, args: dict[str, Any], corpus: Corpus, seen: set[str]) -> tuple[str, dict[str, Any] | None]:
    """(what the model is told, the card to show or None)."""
    if name == "show_code":
        blocks = [b for b in (_block(corpus, x) for x in (args.get("blocks") or [])[:4]) if b]
        if not blocks:
            return "No such block ids. Use ids from the passages, e.g. b12.", None
        return "Shown.", {"kind": "code", "caption": str(args.get("caption") or "")[:120], "blocks": blocks}
    if name == "show_pages":
        pages = [p for p in (_page(corpus, u) for u in (args.get("urls") or [])[:3]) if p]
        if not pages:
            return "Unknown addresses. Use addresses from the passages or the table of contents.", None
        return "Shown.", {"kind": "pages", "pages": pages}
    if name == "show_steps":
        steps = []
        for s in (args.get("steps") or [])[:8]:
            if not isinstance(s, dict) or not s.get("text"):
                continue
            steps.append({"text": str(s["text"])[:300], **({"block": b} if (b := _block(corpus, s.get("block") or "")) else {})})
        if not steps:
            return "No steps given.", None
        return "Shown.", {"kind": "steps", "title": str(args.get("title") or "")[:120], "steps": steps}
    if name == "show_card":
        sp = str(args.get("specimen") or "")
        if sp not in SPECIMENS:
            return f"Unknown specimen; use one of {', '.join(SPECIMENS)}.", None
        return "Shown.", {"kind": "live", "specimen": sp, "about": SPECIMENS[sp]}
    if name == "suggest_next":
        qs = [str(q).strip()[:120] for q in (args.get("questions") or []) if str(q).strip()][:3]
        return "Shown as chips.", ({"kind": "suggest", "items": qs} if qs else None)
    if name == "search_docs":
        found = [c for c in corpus.search(str(args.get("query") or ""), k=5) if c.id not in seen]
        seen.update(c.id for c in found)
        return passages(found) or "Nothing more found.", None
    return f"Unknown tool {name}.", None


async def answer(model: BaseChatModel, corpus: Corpus, question: str, history: list[tuple[str, str]],
                 thread_id: str, run_id: str) -> AsyncIterator[dict]:
    """One answer as AG-UI events (dicts): text first, then the cards, then the follow-ups."""
    yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
    prev = " ".join(t for r, t in history if r == "user")[-400:]
    found = corpus.search(f"{question} {prev}".strip(), k=7)
    if WHOLE_CONFIG.search(question):   # "the whole config": the one-file section, whatever the ranking says
        whole = [c for c in corpus.chunks if c.section == "Every key in one file"]
        found = whole + [c for c in found if c not in whole][:5]
    seen = {c.id for c in found}
    call = f"call_{uuid.uuid4().hex[:12]}"   # the first lookup, shown as a step
    yield {"type": "TOOL_CALL_START", "toolCallId": call, "toolCallName": "search_docs"}
    yield {"type": "TOOL_CALL_ARGS", "toolCallId": call, "delta": json.dumps({"query": question})}
    yield {"type": "TOOL_CALL_END", "toolCallId": call}
    yield {"type": "TOOL_CALL_RESULT", "toolCallId": call, "messageId": f"tool_{uuid.uuid4().hex[:12]}",
           "content": "\n".join(f"{c.title} / {c.section}" for c in found) or "nothing found", "role": "tool"}

    system = SYSTEM.format(specimens="\n".join(f"- {k}: {v}" for k, v in SPECIMENS.items()),
                           toc=corpus.toc or "(none)", passages=passages(found) or "(no passage matched)")
    recipe = recipes.pick(RECIPES, question)   # how to shape this kind of answer (docs_ai/recipes/*.md)
    if recipe:
        log.info("docs recipe: %s", recipe.name)
    system += recipes.instructions(recipe)
    msgs: list[Any] = [SystemMessage(system)]
    for role, text in history:
        msgs.append(HumanMessage(text) if role == "user" else AIMessage(text))
    whole = whole_config_card(corpus) if WHOLE_CONFIG.search(question) else None
    msgs.append(HumanMessage(question if not whole else question + "\n\n(The complete configuration file, YAML and "
                             "Python, is already shown to the reader as a code card. Write one sentence about it, "
                             "do not call show_code, and finish with suggest_next.)"))
    try:
        bound = model.bind_tools(TOOLS)
    except NotImplementedError:
        bound = model
    mid = f"msg_{uuid.uuid4().hex[:12]}"
    started = False
    cards: list[dict[str, Any]] = [whole] if whole else []
    suggest: list[str] = []
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
            msgs.append(AIMessage(content=full.content if full else "", tool_calls=calls))
            for tc in calls:
                name, args = tc.get("name", ""), tc.get("args") or {}
                if name == "search_docs":   # a visible step, like the first lookup
                    sid = tc.get("id") or f"call_{uuid.uuid4().hex[:12]}"
                    yield {"type": "TOOL_CALL_START", "toolCallId": sid, "toolCallName": "search_docs"}
                    yield {"type": "TOOL_CALL_END", "toolCallId": sid}
                result, card = run_tool(name, args, corpus, seen)
                if card and card["kind"] == "suggest":
                    suggest = card["items"]
                elif card:
                    cards.append(card)
                msgs.append(ToolMessage(content=result, tool_call_id=tc.get("id") or ""))
                if name == "search_docs":
                    yield {"type": "TOOL_CALL_RESULT", "toolCallId": sid, "messageId": f"tool_{uuid.uuid4().hex[:12]}",
                           "content": "found" if "<passage" in result else "nothing more", "role": "tool"}
            if suggest and not any(tc.get("name") == "search_docs" for tc in calls):
                break   # the answer is complete: no need for another round
    except Exception as e:  # noqa: BLE001 — a human error, never a stack trace
        log.exception("docs answer failed")
        if started:
            yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
        yield {"type": "RUN_ERROR", "message": "The assistant is unavailable right now. Try again." if "key" not in str(e).lower()
               else "The assistant is not configured (no model key)."}
        return
    if started:
        yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
    if not cards and not started:   # nothing at all: never leave the reader with an empty turn
        pages = [p for p in (_page(corpus, c.doc_id) for c in found[:2]) if p]
        if pages:
            cards.append({"kind": "pages", "pages": pages})
    for card in compose(cards, question):
        yield {"type": "CUSTOM", "name": "docs_card", "value": card}
    if suggest:
        yield {"type": "CUSTOM", "name": "suggestions", "value": {"items": suggest}}
    yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}
