"""Dushes: one assistant for a whole site, above the form agent.

    site = Dushes(form_guide, SiteMap.load("site.yaml"))
    async for ev in site.run(thread_id, message="open the contacts page", state={"page": {"path": "/apply"}, "form": {...}}):
        ...

Each turn goes to one of two agents:
- the form agent: `FormGuide.run`, unchanged, on a page with a form (its own conversation per form, thread
  `<site thread>-<form id>`), and for every card answer;
- Dushes (agent.py): on pages without a form, and on a form page when the message is about the
  site rather than the form (navigation, another page).

A hand-off: Dushes' open_form keeps a note of what the user wants; the next run on the form page
with `forwardedProps.handoff` gives the form agent that note as its first message. With `form_for` (the
host builds the form's state on the server) the form agent answers at once, in the same run.

Host extensions: `context` (live facts in the prompt every turn), `instructions`, `style`, `history`,
`tools` (SiteTool), `suggestions` and `form_for`; each callback gets a SiteRunCtx whose `host` is the
object passed to run(host=...) (create_dushes_router(host=fn) builds it per request).

Knowledge: Dushes reads the site map and the business documents of the site's own namespaces
(`knowledge_namespaces`, default: "site" plus every form on the map), through a search and the document
researcher. The form agent keeps its own form's documents.

One conversation: the site thread's transcript holds every turn the user saw, Dushes' and the
form agents' (their text; their cards stay in the form's own thread), plus the hand-off note, so the chat
and the note survive a reload or a restart. `GET /threads/{id}` returns it for the page.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from ..reply import as_list
from ..stats import RunStats, model_id
from ..transcript import check_thread_id, new_entry

try:   # module level: the router's annotations are resolved here (postponed annotations)
    from fastapi import File, Form, Request, UploadFile
    from fastapi.responses import StreamingResponse
except ImportError:  # pragma: no cover - the HTTP layer is optional
    Request = StreamingResponse = UploadFile = Any  # type: ignore[assignment,misc]
    File = Form = None  # type: ignore[assignment]
from . import agent
from .agent import SiteRunCtx, SiteTool, maybe_await
from .sitemap import SiteMap

if TYPE_CHECKING:
    from ..guide import FormGuide

# a message that is about moving around the site, not about the form on the page
SCOPE = "site"   # the knowledge scope of Dushes
log = logging.getLogger("formguide.site")
_NAV = re.compile(r"\b(go to|go back to|take me|open (the|my|a|an|up)|show me the|navigate|switch to|back to|where (is|can i find)|"
                  r"which page|another page|home ?page|main page)\b", re.I)
# "there", "here": a move that points back into the conversation, so a place in this form on a form page
_HERE = re.compile(r"\b(there|here|to it|this (one|part|section|field|tab|step))\b", re.I)
# navigation words of other languages (written as escapes: the repository is English-only); they send the
# message to the router model rather than straight to Dushes, since "open" may mean a form section too
_NAV_OTHER = re.compile("|".join([
    r"\bgeh(e)? zu\b", r"\b\u00f6ffne\b", r"\bzeig mir die seite\b", r"\bwo finde ich\b",            # German
    r"\bve a\b", r"\bll\u00e9vame\b", r"\babre la p\u00e1gina\b", r"\bd\u00f3nde est\u00e1\b",      # Spanish
    r"\bva \u00e0\b", r"\bemm\u00e8ne-moi\b", r"\bouvre la page\b", r"\bo\u00f9 est\b",             # French
    r"\bvai a\b", r"\bportami\b", r"\bapri la pagina\b", r"\bdov'\u00e8\b",                         # Italian
    "\u043e\u0442\u043a\u0440\u043e\u0439", "\u043f\u0435\u0440\u0435\u0439\u0434\u0438",                    # Russian: open, go to
    "\u0441\u0442\u0440\u0430\u043d\u0438\u0446", "\u0433\u0434\u0435 \u043d\u0430\u0445\u043e\u0434",     # page, where is
    "\u0432\u0456\u0434\u043a\u0440\u0438\u0439", "\u0441\u0442\u043e\u0440\u0456\u043d\u043a",            # Ukrainian: open, page
]), re.I)
# questions about the business itself (where it is, how to reach it, when it is open): a form page's form
# rarely holds those, so the router model decides
_BUSINESS = re.compile("|".join([
    r"\bwhere are you\b", r"\blocated\b", r"\baddress\b", r"\bphone number\b", r"\bopening hours\b",
    r"\bwhen (are|is) (you|it|the \w+) open\b", r"\bhow (do|can) i (get|reach)\b", r"\bcontact (you|us)\b",
    "\u0433\u0434\u0435 \u0432\u044b", "\u0430\u0434\u0440\u0435\u0441", "\u0442\u0435\u043b\u0435\u0444\u043e\u043d",   # Russian: where are you, address, phone
    "\u0447\u0430\u0441\u044b \u0440\u0430\u0431\u043e\u0442",                                         # Russian: opening hours
    "\u0434\u0435 \u0432\u0438", "\u0430\u0434\u0440\u0435\u0441\u0430",                               # Ukrainian: where are you, address
    r"\bwo (seid|sind) (ihr|sie)\b", r"\badresse\b", r"\bd\u00f3nde est\u00e1n\b", r"\bdirecci\u00f3n\b",
    r"\bo\u00f9 \u00eates-vous\b", r"\bdove siete\b", r"\bindirizzo\b", r"\borari\b",
]), re.I)
# a question (rather than a value): its first word, in the languages the widget speaks (escapes: the repository
# is English-only). Slavic words are prefixes, since they change form ("\u0441\u043a\u043e\u043b\u044c\u043a\u043e", "\u043a\u0430\u043a\u043e\u0439/\u043a\u0430\u043a\u0438\u0435").
_ASK = re.compile(r"^\W*(?:(?:" + "|".join([
    r"what|how|when|where|who|which|why|can|could|do|does|did|is|are|will|should",          # English
    r"wie|was|wann|wo|wer|welche\w*|warum|kann|gibt",                                      # German
    r"qu\u00e9|c\u00f3mo|cu\u00e1ndo|d\u00f3nde|qui\u00e9n|cu\u00e1l\w*|cu\u00e1nt\w*|por qu\u00e9",           # Spanish
    r"que|quoi|comment|quand|o\u00f9|qui|quel\w*|combien|pourquoi|est-ce",                       # French
    r"che|cosa|come|quando|dove|chi|qual\w*|quant\w*|perch\u00e9",                             # Italian
    "\u0433\u0434\u0435|\u043a\u043e\u0433\u0434\u0430|\u0447\u0442\u043e|\u043a\u0442\u043e|\u043f\u043e\u0447\u0435\u043c\u0443|\u0437\u0430\u0447\u0435\u043c|\u043c\u043e\u0436\u043d\u043e|\u0435\u0441\u0442\u044c \u043b\u0438",   # Russian: where, when, what, who, why, can, is there
    "\u0434\u0435|\u043a\u043e\u043b\u0438|\u0449\u043e|\u0445\u0442\u043e|\u0447\u043e\u043c\u0443|\u043d\u0430\u0432\u0456\u0449\u043e",   # Ukrainian: where, when, what, who, why
]) + r")\b|" + "|".join([   # words that change form: their stems
    "\u0441\u043a\u043e\u043b\u044c\u043a", "\u043a\u0430\u043a",       # Russian: how many, how / which
    "\u0441\u043a\u0456\u043b\u044c\u043a", "\u044f\u043a",                # Ukrainian: how many, how / which
]) + ")", re.I)


# words in field labels that say nothing about the field ("I have additional income", "Your phone")
_STOP = {"have", "many", "much", "your", "with", "from", "this", "that", "they", "them", "their", "there", "been",
         "more", "other", "into", "than", "only", "also", "each", "some", "will", "would", "about", "after",
         "before", "list", "number", "existing", "yes", "here",
         "\u0435\u0441\u0442\u044c", "\u0432\u0430\u0448", "\u0432\u0430\u0448\u0438", "\u0432\u0430\u0448\u0430", "\u0432\u0430\u0448\u0435", "\u0434\u043b\u044f"}   # Russian: is, your, for


def is_question(text: str) -> bool:
    return text.rstrip().endswith("?") or bool(_ASK.match(text.strip()))


# words about a form itself: a question with one of them is the form's, whatever its fields are called
_FORM_WORDS = (
    "field", "form", "required", "mandatory", "section", "submit", "fill", "missing", "error",
    "feld", "formular", "pflicht", "campo", "formulario", "obligatori", "champ", "formulaire", "modul",
    "\u043f\u043e\u043b\u0435", "\u043f\u043e\u043b\u044f", "\u043f\u043e\u043b\u0435\u0439", "\u0444\u043e\u0440\u043c", "\u0430\u043d\u043a\u0435\u0442", "\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d",   # Russian: field (three forms), form, questionnaire, required
)


def names_a_field(text: str, form: dict[str, Any]) -> bool:
    """The message uses a word of one of the form's field labels (a stem, so "loans" matches "Loan amount" and
    other word forms of the same label match too)."""
    props = ((form or {}).get("config") or {}).get("props") or {}
    words = re.findall(r"\w+", text.lower())
    if any(w.startswith(_FORM_WORDS) for w in words):   # "which fields are still required?": about the form
        return True
    for p in props.values():
        for tok in re.findall(r"\w+", str((p or {}).get("label") or "").lower()):
            if len(tok) >= 4 and tok not in _STOP and not _ASK.match(tok):   # "How many vehicles": not "many"
                stem = tok[:max(4, len(tok) - 2)]
                if any(w.startswith(stem) for w in words):
                    return True
    return False


HISTORY = 6
HANDED = "[Handed over by Dushes]"


def _text_of(out: Any) -> str:
    """A model reply's text (a string, or content blocks with reasoning first)."""
    c = getattr(out, "content", out)
    if isinstance(c, list):
        return "".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type", "text") == "text")
    return str(c or "")


def card_outcome(e: dict[str, Any]) -> str | None:
    """A form card's answer as one line for the site's history: "[Form card] Accepted: Item 5 = Arrosticini"."""
    st, kind = e.get("status"), e.get("kind")
    if st in (None, "pending"):
        return None
    if kind == "card":
        changes = e.get("changes") or []
        names = set(e.get("names") or [c.get("name") for c in changes])
        edited = e.get("edited") or {}
        kept = [f"{c.get('label') or c.get('name')} = {edited.get(c.get('name'), c.get('display') or c.get('value'))}"
                for c in changes if c.get("name") in names]
        if st == "rejected":
            return "[Form card] The user rejected: " + "; ".join(
                f"{c.get('label') or c.get('name')} = {c.get('display') or c.get('value')}" for c in changes)[:600]
        if st == "dismissed":
            return "[Form card] The user closed it without filling anything."
        head = "Accepted" if st == "accepted" else "Accepted in part"
        return f"[Form card] {head}, now in the form: " + "; ".join(kept)[:600]
    if kind == "question":
        a = e.get("answer") or {}
        if st == "dismissed" or not a:
            return "[Form question] The user skipped it."
        picked = ", ".join(str(o.get("label") or o.get("id")) for o in e.get("options") or [] if o.get("id") in (a.get("ids") or []))
        said = picked or str(a.get("text") or "")
        return f"[Form question] {e.get('question', '')} The user answered: {said}" + (" (filled in the form)" if e.get("applied") else "")
    if kind == "confirm":
        return f"[Form confirmation] {e.get('title', '')}: the user {'confirmed' if st == 'accepted' else 'declined'}."
    if kind == "upload":
        return "[Form upload] The user attached a file." if st == "answered" else "[Form upload] The user skipped it."
    return None


def with_hand_back(caps: Any) -> list[str]:
    """The client's capabilities plus hand_back (none sent: every card, as an older client gets)."""
    from ..agent.actions import ACTION_CAPS, VARIANTS

    base = list(caps) if isinstance(caps, (list, tuple)) else [*dict.fromkeys(ACTION_CAPS.values()), *VARIANTS]
    return [*base, "hand_back"] if "hand_back" not in base else base


def handoff_message(note: str, language: str = "") -> str:
    """The form agent's first message after a hand-off."""
    say = f" Reply to the user in {language}." if language else ""
    return f"{HANDED} On the site the user said: {note}{say}"



class Said:
    """A form agent's words of one run, by message: a lead it takes back (CUSTOM text_retract) is left out."""

    def __init__(self) -> None:
        self.parts: dict[str, str] = {}
        self.cards: list[dict[str, Any]] = []   # display cards of the run: kept after its words, so a reload shows them

    def see(self, ev: dict[str, Any]) -> None:
        if ev["type"] == "CUSTOM" and ev.get("name") == "card":
            self.cards.append(ev.get("value") or {})
        elif ev["type"] == "TEXT_MESSAGE_CONTENT":
            self.parts[ev["messageId"]] = self.parts.get(ev["messageId"], "") + ev["delta"]
        elif ev["type"] == "CUSTOM" and ev.get("name") == "text_retract":
            self.parts.pop(str((ev.get("value") or {}).get("messageId")), None)

    def text(self) -> str:
        return "".join(self.parts.values())

    def first_id(self) -> dict[str, str]:
        """{"message_id": the run's first kept message} for its transcript entry, or {}."""
        mid = next(iter(self.parts), None)
        return {"message_id": mid} if mid else {}

stats_log = logging.getLogger("formguide.stats")


def _voice_on(thread_id: str) -> bool:
    from .. import voice
    return voice.active(thread_id)


class Dushes:
    def __init__(self, form_guide: FormGuide, site: SiteMap, model: Any = None,
                 knowledge_namespaces: list[str] | None = None, router_model: Any = None, *,
                 context: Any = None, instructions: str = "", style: str | None = None, history: int = HISTORY,
                 tools: list[SiteTool] | None = None, suggestions: bool = False, form_for: Any = None,
                 stay_on_forms: bool = True):
        self.forms = form_guide
        self.context = context            # (ctx) -> str | Awaitable[str]: live facts, in the prompt every turn
        self.instructions = instructions  # added to the site map's own instructions
        self.style = style                # replaces the default reply length rule
        self.history = history            # past turns Dushes sees
        self.tools = list(tools or [])    # the host's SiteTools
        self.suggestions = suggestions    # suggest_next -> CUSTOM suggestions
        self.form_for = form_for          # (form_id, ctx) -> form state | None: the same-run hand-off
        self._offers: dict[str, bool] = {}   # conversations whose last answer offered to open a page or a form
        self.stay_on_forms = stay_on_forms   # on a form page, answer in place while the user fills the form in
        from .. import intent as _intent
        self.intent = _intent.Layer(_intent.Settings.from_env())   # the choice layer; off unless the launcher sets it
        self.site = site
        self.model = model   # Dushes' model; default: the form guide's agent model
        self._router_model = router_model   # a cheap model for unclear messages; default: the run's memory model
        # the site's documents: the "site" namespace and the forms' own, seen through one knowledge scope
        spaces = knowledge_namespaces or ["site", *dict.fromkeys(p.form for p in site.pages if p.form)]
        self.forms.knowledge.scopes.setdefault(SCOPE, list(spaces))

    @property
    def router_model(self) -> Any:
        """The model that decides an unclear message: the one given, else the memory model of the run's choice."""
        return self._router_model or self.forms.models.memory

    @router_model.setter
    def router_model(self, value: Any) -> None:
        self._router_model = value

    # ------------------------------------------------------------ the site's documents
    def doc_passages(self, question: str, k: int = 3) -> str:
        kb = self.forms.knowledge
        hits = kb.search(SCOPE, question, k=k) if kb.documents_for(SCOPE) else []
        return "\n\n".join(f"<document title=\"{c.title} / {c.section}\">\n{c.text}\n</document>" for _s, c in hits)

    async def ask_documents(self, question: str) -> str:
        return await self._ask_documents(question)

    async def _ask_documents(self, question: str, usage: list | None = None) -> str:
        """`usage`, when given, collects the usage of the researcher's model calls (for run_stats)."""
        from ..knowledge import research   # needs the `research` extra (deepagents)

        return await research.ask_documents(self.forms.knowledge, SCOPE, self.site.title, question,
                                            self.forms.models.research, usage=usage)

    # ------------------------------------------------------------ the hand-off note, kept in the transcript
    def _keep_note(self, thread_id: str, form_id: str, note: str, language: str = "", status: str = "pending") -> None:
        self.forms.transcripts.append(thread_id, new_entry("handoff", form_id=form_id, note=note, language=language,
                                                           status=status))

    def _take_note(self, thread_id: str, form_id: str) -> tuple[str, str] | None:
        tx = self.forms.transcripts
        e = next((x for x in reversed(tx.list(thread_id)) if x["kind"] == "handoff" and x.get("status") == "pending"), None)
        if not e:
            return None
        tx.update(thread_id, e["id"], status="used")
        return (e.get("note") or "", e.get("language") or "") if e.get("form_id") == form_id else None

    # ------------------------------------------------------------ routing
    def route(self, message: str | None, state: dict[str, Any], resume: Any = None, handoff: bool = False,
              thread_id: str | None = None) -> str:
        """'form', 'site', or 'unclear' (a form page and a message that names another page's words, without
        asking to go anywhere: a cheap model decides, see classify)."""
        form = state.get("form") or None
        if resume is not None:
            return "form" if form else "site"
        if not form:
            return "site"
        if handoff or not message:
            return "form"
        return self._about_site(message, state, thread_id)

    def _other_page(self, text: str, here: Any) -> bool:
        """The message names another page of the site by its title or keywords (the form page's own words do not count)."""
        own = set(here.keywords) | {here.title.lower()} if here else set()
        for p in self.site.pages:
            if here and p.path == here.path:
                continue
            words = [w for w in (p.title.lower(), *p.keywords) if w not in own]
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words if len(w) > 2):
                return True
        return False

    def _titled(self, message: str, here: Any) -> Any:
        """The page (other than this one) whose whole title is said in the message, the longest such title."""
        text = " " + " ".join(re.findall(r"\w+", (message or "").lower())) + " "
        hits = [p for p in self.site.pages if not (here and p.path == here.path)
                and (t := " ".join(re.findall(r"\w+", p.title.lower()))) and f" {t} " in text]
        return max(hits, key=lambda p: len(p.title)) if hits else None

    def _with_page(self, form: dict[str, Any], state: dict[str, Any], form_id: str | None = None) -> dict[str, Any]:
        """The form's state with the facts of the page it sits on (the site map's text for that page), so the form
        agent can answer from the page too. A host's own `page` in the form state is kept."""
        if not isinstance(form, dict) or form.get("page"):
            return form
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        if form_id and not (here and here.form == form_id):   # a hand-off: the page that holds this form
            here = next((p for p in self.site.pages if p.form == form_id), here)
        return {**form, "page": here.facts()} if here else form

    def _last_speaker(self, thread_id: str | None) -> tuple[str, str]:
        """('site' | 'form' | '', what they said last) from the site transcript (form turns carry form_id)."""
        if not thread_id:
            return "", ""
        e = next((x for x in reversed(self.forms.transcripts.list(thread_id)) if x["kind"] == "assistant" and x.get("text")), None)
        if not e:
            return "", ""
        return ("form" if e.get("form_id") else "site"), str(e.get("text") or "")

    def _about_site(self, message: str, state: dict[str, Any], thread_id: str | None = None) -> str:
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        text = message.lower()
        if _NAV.search(text):   # an explicit move: go to, open, take me ...
            if self._other_page(text, here):
                return "site"   # to another page of the site
            if _HERE.search(text) or names_a_field(message, state.get("form") or {}):
                return "form"   # "take me there", "open the income section": a place in this form
            return "unclear"
        if self._titled(message, here):
            # another page of the site, said by its whole title ("can you open car insurance", "I said car
            # insurance"): Dushes sees the site and the form agent does not, so the form agent is never the first
            # to get such a line. Decided here, in code: told to hand such a line back, the form agent answered
            # "there is no such section in this form" instead, and argued on a repeat (the QA Lead, 2026-11-17)
            return "site"
        if _NAV_OTHER.search(text):
            return "unclear"   # a move in another language, or a form section: the model decides
        if _BUSINESS.search(text):
            return "unclear"   # where the business is, how to reach it: rarely the form's
        if self._other_page(text, here):
            return "unclear"   # "a car loan" on the loan form is the form's; "the barbershop prices" is not
        if self._last_speaker(thread_id)[0] == "site":
            return "unclear"   # Dushes spoke last: the message may answer it
        if is_question(message) and not names_a_field(message, state.get("form") or {}):
            return "unclear"   # a question about none of this form's fields ("how many new requests?")
        return "form"

    def _by_rule(self, message: str, state: dict[str, Any], thread_id: str | None = None) -> str:
        """'form' or 'site' for an unclear message without a model call (a voice conversation: the router model
        would add its whole call to the wait). A move or a question about the business is the site's; a message
        that names a field of this form is the form's; another question, an answer to what Dushes just asked or
        offered, or words about another page are the site's; anything else on a form page is a value for the form."""
        from ..voice import yes_or_no
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        text = message.lower()
        if _NAV.search(text) or _NAV_OTHER.search(text) or _BUSINESS.search(text) or self._titled(message, here):
            mode = "site"
        elif names_a_field(message, state.get("form") or {}):
            mode = "form"
        elif is_question(message) or self._other_page(text, here):
            mode = "site"
        elif self._last_speaker(thread_id)[0] == "site" and (
                yes_or_no(message) is not None or self._last_speaker(thread_id)[1].rstrip().endswith("?")):
            mode = "site"   # Dushes asked something, or offered: this answers it
        else:
            mode = "form"
        log.info("site route by rule: %r -> %s", message[:60], mode)
        return mode

    async def classify(self, message: str, state: dict[str, Any], thread_id: str | None = None,
                       stats: RunStats | None = None) -> str:
        """One word from a cheap model for an unclear message on a form page; 'form' when it cannot tell."""
        import asyncio

        from langchain_core.messages import HumanMessage

        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        form = (state.get("form") or {}).get("form_id") or (here.form if here else "")
        prompt = (f"Decide who answers a chat message on the site \"{self.site.title}\". The user is on the page "
                  f"\"{here.title if here else '?'}\" with the form \"{form}\". {self._spoke_line(thread_id)}"
                  f"The message: \"{message[:500]}\"\n"
                  "form: the message gives a value for this form, asks about its fields or choices, or answers the "
                  "form assistant's question.\n"
                  "site: the message asks about the business or the site itself: where it is (address, location, how "
                  "to get there), contacts, opening hours, another page or service, or it answers the site "
                  "assistant's question. A question about where the business is or when it is open is site even "
                  "right after the form assistant spoke.\n"
                  "Answer with one word: form or site.")
        t_call = RunStats.now()
        try:
            out = await asyncio.wait_for(self.router_model.ainvoke([HumanMessage(prompt)]), timeout=4)
        except Exception as e:  # noqa: BLE001 — never block a turn on the router
            log.warning("site router failed (%s): the turn stays with the form", type(e).__name__)
            return "form"
        if stats is not None:
            stats.model_call(t_call, None, dict(getattr(out, "usage_metadata", None) or {}), kind="router",
                             model=model_id(self.router_model))
        word = _text_of(out).strip().lower()
        log.info("site router: %r -> %s", message[:60], word[:20])
        return "site" if word.startswith("site") else "form"

    def _filling(self, thread_id: str, state: dict[str, Any]) -> bool:
        """The user is on a page with a form to fill in, and stay_on_forms is on (a host whose form page is a
        studio rather than a form to finish turns it off)."""
        return bool(self.stay_on_forms and state.get("form"))

    def _spoke_line(self, thread_id: str | None) -> str:
        who, said = self._last_speaker(thread_id)
        if not who:
            return ""
        name = "Dushes" if who == "site" else "the form assistant"
        return f"The last to speak was {name}: \"{said[-300:]}\". "

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
        msgs = [{"id": e["id"], "role": "activity", "activityType": "card", "activity": e.get("card") or {}} if e["kind"] == "display" else
                {"id": (e.get("message_id") or e["id"]) if e["kind"] == "assistant" else e["id"], "role": e["kind"], "content": e.get("text", ""),
                 **({"reply_to": as_list(e["reply_to"])} if e["kind"] == "user" and e.get("reply_to") else {}),
                 # who answered: a form agent's words carry the form id in the site thread
                 **({"agent": "form" if e.get("form_id") else "dushes"} if e["kind"] == "assistant" else {})}
                for e in self.forms.transcripts.list(thread_id)
                if (e["kind"] in ("user", "assistant") and e.get("text")) or (e["kind"] == "display" and e.get("card"))]
        pending = None
        if form_id:
            pending = self.forms.thread(f"{thread_id}-{form_id}"[:100]).get("pending_card")
        return {"thread_id": thread_id, "messages": msgs, "pending_card": pending,
                "transcription": bool(self.forms.transcriber)}

    # ------------------------------------------------------------ a turn
    async def run(self, thread_id: str, *, message: str | None = None, state: dict[str, Any] | None = None,
                  resume: dict[str, Any] | None = None, run_id: str | None = None, handoff: bool = False,
                  host: Any = None, reply_to: list[dict[str, Any]] | None = None, model: str | None = None,
                  **form_kwargs: Any) -> AsyncIterator[dict]:
        """One run as AG-UI events. Dushes' own model calls (its answers, the router, its document researcher)
        are reported in a CUSTOM `run_stats` event with `agent: "site"`, right before the terminal event; a form
        agent's turn in the same run reports its own, as it does alone.

        `model`: a name from `models.choices`. The site conversation keeps the choice of its first run, and the
        form agents it hands to run on the same one; a CUSTOM `model` event follows RUN_STARTED."""
        from ..guide import _choice
        from ..stats import model_id as _model_id
        check_thread_id(thread_id)
        choice = self.forms.check_model(thread_id, model)
        if choice:
            if self.forms.thread_choice(thread_id) is None:
                self.forms.transcripts.append(thread_id, new_entry("model", choice=choice))
            form_kwargs = {**form_kwargs, "model_bound": choice}   # its form threads follow the site thread
        _choice.set(choice)
        told = False
        run_id = run_id or str(uuid.uuid4())
        stats = RunStats(run_id, thread_id)
        stats.agent = "site"
        stats.choice = choice
        seen: dict[str, Any] = {"said": [], "screen": [], "label": ""}   # for the demo's own log of the turn
        async for ev in self._run(thread_id, stats, message=message, state=state, resume=resume, run_id=run_id,
                                  handoff=handoff, host=host, reply_to=reply_to, **form_kwargs):
            if ev.get("type") == "TEXT_MESSAGE_START" and seen["said"]:
                seen["said"].append("\n")
            if ev.get("type") == "TEXT_MESSAGE_CONTENT":
                seen["said"].append(str(ev.get("delta") or ""))
            elif ev.get("type") == "CUSTOM" and ev.get("name") in ("site_directive", "card", "display", "ui_directive", "on_interrupt"):
                value = ev.get("value")
                if ev["name"] == "on_interrupt" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        value = None
                seen["screen"].append({"name": ev["name"], "value": value})
            if ev.get("type") == "CUSTOM" and ev.get("name") == "model":
                continue   # the form agent's: this run already said which model answers
            if choice and not told and ev.get("type") == "RUN_STARTED":
                told = True
                s = self.forms._choices[choice]
                yield ev
                yield {"type": "CUSTOM", "name": "model",
                       "value": {"choice": choice, "label": s.label, "model": _model_id(self.model or s.models.agent)}}
                continue
            if ev.get("type") == "RUN_FINISHED" and os.environ.get("INTENT_LABELS") == "1":
                fast = getattr(stats, "fast", None)
                who = self.intent.settings.provider.capitalize()
                if fast and fast.get("handled") and fast.get("by"):
                    label = f"in code ({fast['by']}) \u00b7 no model"
                elif fast and fast.get("handled") and fast.get("did"):
                    name = str(_model_id(self.model or self.forms.models.agent))
                    rest = max(RunStats.now() - stats.t0 - fast["ms"] / 1000, 0.0)
                    label = (f"{who} \u00b7 {fast['ms']} ms: opened {fast['did']} \u00b7 then "
                             f"{'Haiku' if 'haiku' in name.lower() else name} \u00b7 {rest:.1f} s")
                elif fast and fast.get("handled"):
                    label = f"{who} \u00b7 {fast['ms']} ms"
                elif getattr(stats, "decided", False):
                    label = self.__dict__.get("_mixed", {}).pop(thread_id, "")   # what the layer did a run ago, if not said yet
                else:
                    name = str(_model_id(self.model or self.forms.models.agent))
                    took = RunStats.now() - stats.t0
                    why = f"no answer within {self.intent.settings.timeout_ms} ms" if fast and fast.get("late") else "not sure"
                    asked = f" (after {who} {fast['ms']} ms: {why})" if fast else ""
                    label = f"{'Haiku' if 'haiku' in name.lower() else name} \u00b7 {took:.1f} s{asked}"
                heard = getattr(self, "_heard", None)
                mixed = self.__dict__.get("_mixed", {})
                if fast and fast.get("handled") and thread_id in mixed and not fast.get("did"):
                    mixed[thread_id] = f"{label}: {mixed[thread_id]}"       # said with the model's part, in the next run
                    label = ""
                elif label and thread_id in mixed and not fast and not stats.models:
                    label = ""                                              # a run with no model in it: said with the next one
                elif label and thread_id in mixed and not fast:
                    label = f"{mixed.pop(thread_id)} \u00b7 then {label}"
                if label and heard and RunStats.now() - heard[0] < 30:   # this line was dictated: how long the speech took to read
                    label = f"heard in {heard[1]} ms \u00b7 {label}"
                    self._heard = None
                if label:
                    lid = f"label_{uuid.uuid4().hex[:10]}"
                    yield {"type": "TEXT_MESSAGE_START", "messageId": lid, "role": "assistant"}
                    seen["label"] = label
                    yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": lid, "delta": f"\u2014 {label}"}
                    yield {"type": "TEXT_MESSAGE_END", "messageId": lid}
            if ev.get("type") in ("RUN_FINISHED", "RUN_ERROR") and os.environ.get("INTENT_SCORES") == "1" and getattr(stats, "fast", None):
                yield {"type": "CUSTOM", "name": "choice_scores", "value": {
                    k: stats.fast.get(k) for k in ("ms", "tokens", "targets", "sure", "handled", "late") if k in stats.fast}}
            if ev.get("type") in ("RUN_FINISHED", "RUN_ERROR") and os.environ.get("INTENT_TRACE") == "1" and getattr(stats, "trace", None):
                yield {"type": "CUSTOM", "name": "decision_trace", "value": _decision_trace(
                    stats, seen, run_id, thread_id in self.__dict__.get("_mixed", {}), self.site)}
            if ev.get("type") in ("RUN_FINISHED", "RUN_ERROR"):
                _demo_log(thread_id, message, resume, handoff, state, stats, seen, ev["type"])
            if ev.get("type") in ("RUN_FINISHED", "RUN_ERROR") and stats.models:
                summary = stats.as_event()
                stats.models = []   # once per run
                stats_log.info(json.dumps(summary, ensure_ascii=False))
                yield {"type": "CUSTOM", "name": "run_stats", "value": summary}
            yield ev

    async def _run(self, thread_id: str, stats: RunStats, *, message: str | None, state: dict[str, Any] | None,
                   resume: dict[str, Any] | None, run_id: str, handoff: bool, host: Any,
                   reply_to: list[dict[str, Any]] | None, **form_kwargs: Any) -> AsyncIterator[dict]:
        check_thread_id(thread_id)
        state = state or {}
        fid0 = str((state.get("form") or {}).get("form_id") or "form")
        form_thread0 = f"{thread_id}-{fid0}"[:100]
        from .. import intent as _intent
        if (resume is not None or handoff) and _intent.has_preset(form_thread0):
            stats.decided = True                     # a step the layer decided before: the closing line of a value,
            #                                          or the section of a path, opened once its page has loaded
        elif message:
            _intent.clear_preset(form_thread0)        # a new message: nothing decided is left over
        fast = None
        # INTENT_LAYER=0 (the measurement's "tool only" arm): nothing is decided in front of the model, neither by
        # the chooser nor in code; every line goes to the model, which still has the choice tool
        if message and resume is None and not handoff and os.environ.get("INTENT_LAYER", "1") != "0":
            fast = self._taken_up(thread_id, message, stats) or await self._fast(thread_id, message, state, stats)
        if fast and fast["kind"] in ("navigate", "show"):
            tail = bool(fast.get("tail"))
            async for ev in self._fast_move(thread_id, message, run_id, fast, reply_to):
                if not (tail and ev["type"] == "RUN_FINISHED"):
                    yield ev
            if not tail:
                return
            # the agent answers what is left of the line, on the page that is open now, and knows what was done
            there = {**state, "page": {**(state.get("page") or {}), "path": fast["args"].get("path") or "/"}}
            done = (f'Already done for this message, before you: "{fast["title"]}" was opened and is on the screen now, '
                    f'and the person was told "{fast["title"]}." Do not open it again and do not announce it. Answer '
                    "only what is left of the message, shortly.")
            async for ev in self._site_turn(thread_id, message, there, run_id, host, form_kwargs, recorded=True,
                                            reply_to=reply_to, stats=stats, done=done):
                if ev["type"] != "RUN_STARTED":       # one run
                    yield ev
            return
        if fast and fast["kind"] in ("value", "focus"):
            mode = "form"
        elif fast and fast["kind"] == "agent":
            mode = fast["mode"]                       # the layer could not act, and knows whose turn it is
        else:
            mode = self.route(message, state, resume, handoff, thread_id)
        if mode == "unclear":
            from .. import voice
            # a spoken message is not held for the router model: a rule places it, and whoever gets it can give
            # it to the other in the same run (to_form, hand_back)
            mode = (self._by_rule(message or "", state, thread_id) if voice.active(thread_id)
                    else await self.classify(message or "", state, thread_id, stats))
        if mode == "form":
            form = self._with_page(state["form"], state)
            fid = str(form.get("form_id") or "form")
            kw: dict[str, Any] = dict(form_kwargs)
            taken = self._take_note(thread_id, fid) if handoff and not message else None
            typed = message
            if taken:
                # the request the user made elsewhere on the site, as the form agent's first message: it then
                # proposes what the note covers with its usual tools and cards
                message = handoff_message(*taken)
            form_thread = f"{thread_id}-{fid}"[:100]
            self._carry_files(thread_id, form_thread, form, resume)
            tx = self.forms.transcripts
            if typed:
                tx.append(thread_id, new_entry("user", text=typed, form_id=fid, **({"reply_to": as_list(reply_to)} if reply_to else {})))
            kw["capabilities"] = with_hand_back(kw.get("capabilities"))   # the form agent may give the message back
            from ..transcript import pending_card
            open_card = pending_card(tx.list(form_thread)) if resume is not None else None
            said = Said()
            back = None
            if typed and reply_to:
                kw["reply_to"] = reply_to   # the form agent reads the quote too
            async for ev in self.forms.run(form_thread, message=message, state=form, resume=resume,
                                           run_id=run_id, **kw):
                if ev["type"] == "CUSTOM" and ev.get("name") == "hand_back":
                    back = ev.get("value") or {}
                    continue
                if back is not None:   # the form's turn ended with hand_back: Dushes answers next
                    continue
                said.see(ev)
                yield ev
            if open_card:   # what the user did with the form's card, as a fact the site agent and the router see
                done = next((e for e in tx.list(form_thread) if e["id"] == open_card["id"]), None)
                fact = card_outcome(done) if done else None
                if fact:
                    tx.append(thread_id, new_entry("card_result", text=fact, form_id=fid))
            if said.text().strip():
                tx.append(thread_id, new_entry("assistant", text=said.text(), form_id=fid, **said.first_id()))
            for card in said.cards:
                tx.append(thread_id, new_entry("display", card=card, form_id=fid))
            if back is None or not typed:
                return
            async for ev in self._site_turn(thread_id, typed, state, run_id, host, form_kwargs, recorded=True,
                                            reply_to=reply_to, stats=stats):
                if ev["type"] != "RUN_STARTED":   # one run: the form's RUN_STARTED already went out
                    yield ev
            return
        async for ev in self._site_turn(thread_id, message, state, run_id, host, form_kwargs, reply_to=reply_to,
                                        stats=stats):
            yield ev

    # ------------------------------------------------------------ the choice layer (demo branch)
    async def _fast(self, thread_id: str, message: str, state: dict[str, Any], stats: RunStats) -> dict[str, Any] | None:
        """The choice layer. The owner's decision (2026-11-17): the target of a line (a page, a tab, a section, a
        field for a value) is always chosen by the chooser, never matched in code. It is given the whole site as
        paths, what is on the screen, the form's structure as the form's own assistant gets it, and the last ten
        messages; one call. Code only carries the chosen path out, checks the state, and keeps the prohibitions:
        a date never moves the person, a consent is never an option, nothing private leaves, only an action that
        can be undone, and only on the person's own request. None: the agent's turn."""
        from .. import intent as _intent
        from ..language import detect
        layer = self.intent
        if layer.settings.provider == "off":
            return None
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        if os.environ.get("INTENT_CODE") == "1":
            # only for the measurement's "code" arm: the names said are settled in code and no chooser is asked
            named = self._bare_value(thread_id, message, state, stats) or await self._named(thread_id, message, state, here, stats)
            return named or ({"kind": "agent", "mode": "site"} if self._titled(message, here) else None)
        if not layer.on:
            return None
        # the form on the screen, as it is now
        form, ov, lay, pack = state.get("form") or None, None, None, None
        if isinstance(form, dict) and form.get("config"):
            try:
                from ..form.overlay import Overlay
                lay = self.forms.layout(form.get("jsx_hash", ""))
                pack = self.forms.packs.get(form.get("form_id"))
                ov = Overlay(lay, form["config"], pack.pii) if lay is not None else None
            except Exception:  # noqa: BLE001 - a form the layer cannot read is the agent's
                ov = None
        # the whole site as paths: pages, their tabs and sections, each form's tabs, steps and sections
        targets: list[Any] = []
        for p in self.site.pages:
            on = bool(here and p.path == here.path)
            # the owner (2026-11-17): a place asked for by what is there ("where I can book a haircut") or with a slip
            # of the tongue is the chooser's too, so each option carries the host's own description and keywords
            describe = os.environ.get("INTENT_DESCRIBE", "1") != "0"
            short = lambda t, n: " ".join(str(t or "").split())[:n]   # noqa: E731
            if not on:
                targets.append(_intent.Option(f"screen:{p.path}", p.title, "; ".join(
                    x for x in (short(p.description, 90), ", ".join(p.keywords[:6])) if x) if describe else ""))
            targets += [_intent.Option(f"part:{p.path}#{x.id}", f"{p.title} \u203a {x.title}", short(x.text, 70) if describe else "")
                        for x in p.parts]
            if p.form:
                try:
                    tree = self._tree_of(form, seen_only=True) if on and ov is not None else await self._form_tree(p.form)
                except Exception:  # noqa: BLE001
                    tree = []
                targets += [_intent.Option(f"form:{p.path}:{name}", " \u203a ".join([p.title, *ups, label])) for name, label, ups in tree]
        targets = targets[:_intent.MAX_OPTIONS - 1]
        # a person's or a company's name the screen does not show never leaves: it goes as "<name>", and the line
        # then always has more in it for the agent (a name is a text for a field, never the chooser's)
        vq0 = _intent.value_question(ov, set(pack.consents or {})) if ov is not None else None
        sent, named = _intent.mask_names(message, [o.label for o in targets] + ([q.label for q in vq0.options] if vq0 else []))
        qs: dict[str, Any] = {
            "is_command": _intent.command_question(),
            "kind": _intent.Question("choice", "turn", "What kind of line is it?", (
                _intent.Option("go_to", "an order to go to a section or open an item"),
                _intent.Option("show", "an order to highlight, scroll to or point at something"),
                _intent.Option("set_value", "an order to set a value the line names outright, or a bare value for a field on the screen"),
                _intent.Option("question", "where, how, why, what, can I"),
                _intent.Option("other", "a text to write, a judgement or a suggestion"))),
            "needs_agent": _intent.Question("noul", "needs_agent", "Does the line name a person or a company that is not "
                                            "on the screen, ask a question, ask for a text, or need judgement?"),
            "asks_move": _intent.Question("noul", "asks_move", "Does the line, in any part of it, order to open, go to "
                                          "or show a page, a tab or a section?"),
            "asks_more": _intent.Question("noul", "asks_more", "Beside an order to open, show or set something, does the "
                                          "line ask anything else: a question, an explanation, a text to write, "
                                          "an opinion?"),
            "target": _intent.Question("choice", "target", "Which object of the site does the line ask to open or show? "
                                       "The line may say the way to it, or only its name, or point back at what the "
                                       "conversation just offered or opened.", tuple(targets), act="show")}
        iso, beside = _intent.spoken_date(message), ""
        if not iso:
            iso, beside = _intent.date_in(message)   # a date inside a longer line ("Lugansk, 1st July '92")
        if ov is not None:
            vq = _intent.value_question(ov, set(pack.consents or {}))
            if vq:
                qs["value"] = vq
            if iso:   # a date said: which date field of the form on the screen it is for (the value itself is read in code)
                dates = [n for n in lay.fields() if n.role == "date" and ov[n.name].editable]
                if dates:
                    qs["date_field"] = _intent.Question("choice", "date_field", "Which date field is this date for?", tuple(
                        _intent.Option(n.name, " \u203a ".join([*(str(ov[x.name].label) for x in lay.ancestors(n.name)
                                                                 if ov.get(x.name) is not None and ov[x.name].label),
                                                               str(ov[n.name].label or n.name)])) for n in dates), act="set_field")
        shown_fields: list[str] = []
        if ov is not None:
            # a question a field for the choice fields the person has on the screen now, so one line can set several
            from ..form.render import locate
            loc = locate(ov, form.get("ui"))
            # the fields in open sections first, then the rest of the open tab or step: a page does not always
            # report which sections are open, and a value said for a folded section is still a value of this tab
            ui = form.get("ui") or {}
            wide = locate(ov, {**ui, "openAccordions": [n.name for n in lay.nodes.values() if n.role == "accordion"]})
            for where in (loc.on_screen, wide.on_screen):
                for n in lay.fields():
                    c = lay.nearest_container(n.name)
                    if c is not None and c.name in where and ov[n.name].visible and n.name not in shown_fields:
                        shown_fields.append(n.name)
            per_field = _intent.field_questions(ov, shown_fields, set(pack.consents or {}))
            qs.update(dict(list(per_field.items())[:16]))
            # and a yes / no a section of the open tab, so one line can open several
            sections = [n for n in lay.nodes.values() if n.role in ("accordion", "section") and n.name and n.parent in wide.on_screen
                        and ov.get(n.name) is not None and ov[n.name].visible and ov[n.name].label][:10]
            if sections:
                qs["all_sections"] = _intent.Question("noul", "all_sections", "Does the line ask to open all the sections, "
                                                      "every one of them, of a tab or of the page?", act="show")
            for n in sections:
                qs[f"s:{n.name}"] = _intent.Question("noul", f"section:{n.name}",
                                                     f'Does the line ask to open or show the section "{ov[n.name].label}"?', act="show")
        if ov is None and any(len([x for x in p.parts if x.kind in ("accordion", "section")]) >= 2 for p in self.site.pages):
            qs["all_sections"] = _intent.Question("noul", "all_sections", "Does the line ask to open all the sections, "
                                                  "every one of them (all the questions, all the parts), of a page?", act="show")
        if "all_sections" in qs:
            qs["other_place"] = _intent.Question("noul", "other_place", "Does the line name a page, a tab or a step other "
                                                 "than the one that is on the screen now?", act="show")
        context = self._context(thread_id, state, here, ov, lay, pack)
        started = RunStats.now()
        asked: list[dict[str, Any]] = []
        picks = await layer.pick_many(sent, detect(message) or "en", qs, here.path if here else "", context, asked)
        ms = round((RunStats.now() - started) * 1000)
        stats.fast = {"ms": ms, "handled": False, "late": not picks and ms >= layer.settings.timeout_ms - 10}
        # how the turn was decided, for a host that shows it to the person themself (CUSTOM decision_trace): the
        # line as it left the filter, every question with its answer, the bars; what was applied is added at the end
        stats.trace = {"said": _intent.scrub(layer, sent), "questions": asked, "threshold": layer.settings.threshold,
                       "bars": {"field": 0.8, "section": 0.8, "bare_value": 0.9, "tail": float(os.environ.get("INTENT_TAIL", "0.7"))},
                       "filtered": {"names": sent.count("<name>"),
                                    "emails": sum(1 for m in _intent._PRIVATE_BITS.finditer(message) if m.group(1)),
                                    "phones_or_digits": sum(1 for m in _intent._PRIVATE_BITS.finditer(message) if m.group(2))},
                       "chooser_by": getattr(layer.chooser, "by", ""), "why": "name_masked" if named else ""}
        # the demo's terminal shows what the chooser was sure of (ids and confidences only, never the phrase)
        stats.fast.update(tokens=getattr(layer.chooser, "tokens", None), targets=len(targets),
                          sure={k: [v.id, round(v.confidence, 2)] for k, v in picks.items()})
        log.warning("choice layer: %d ms, %s input tokens, %d targets, sure of %s", ms, getattr(layer.chooser, "tokens", "?"),
                    len(targets), {k: (v.id, round(v.confidence, 2)) for k, v in picks.items()})
        fid = str((form or {}).get("form_id") or "form")
        def fields_named(moving: bool) -> list[tuple[str, Any, str, str]]:
            """Every choice field or tick of the screen the chooser is sure of and the line names: (field, value,
            the field's label, the option as shown)."""
            many: list[tuple[str, Any, str, str]] = []
            same = ov is None or (detect(message) or "en") == (detect(" ".join(
                str(ov[n.name].label or "") for n in lay.nodes.values() if ov.get(n.name) is not None)[:600]) or "en")
            for key, p in picks.items():
                # the CPO (2026-11-17): for a field on the screen "is it a command" does not matter; the value
                # counts at 0.8, or at 0.7 when it is 0.2 clear of the second option, and its field or option is
                # said in the line. The QA Lead calibrates both numbers
                clear = getattr(layer.chooser, "margins", {}).get(key, 0.0) >= 0.2
                if not key.startswith("f:") or ov is None or moving or not (p.confidence >= 0.8 or (p.confidence >= 0.7 and clear)):
                    continue
                fname, _, opt = p.id.partition("=")
                fe = ov.get(fname)
                if fe is None or not fe.editable:
                    continue
                flabel = str(fe.label or fname)
                is_bool = fe.node.role == "bool"
                fshown = ("yes" if opt == "true" else "no") if is_bool else next(
                    (str(o.get("name")) for o in fe.options or [] if str(o.get("id")) == opt), opt)
                # the line must itself say the field or the option: a word of the label without its bracketed note
                # ("Add hair wash (+$10, +15 min)" is said as "hair wash"), or a word of the option
                plain = re.sub(r"\(.*?\)", " ", flabel)
                from .. import voice as _voice
                everyday = bool(_voice._SAME.get(fshown.strip().lower(), set()) & set(re.findall(r"[\w']+", message.lower())))
                if (_intent.says_any(plain, message) or (not is_bool and _intent.says_any(fshown, message)) or everyday
                        or (not same and p.confidence >= 0.9)):   # "a woman" says Female
                    many.append((fname, (opt == "true") if is_bool else opt, flabel, fshown))
            return many

        out: dict[str, Any] | None = None
        tail = False
        if iso and "date_field" in picks and ov is not None:
            # a bare date is a value, with or without a verb; it never moves the person anywhere
            name = picks["date_field"].id
            # what else the line says (a place, a name) is the form assistant's, which goes on after the card
            tail = bool(named or _intent.says_more(beside))
            # and the list options or ticks the same line names ("I am a woman, born 1st July '92")
            also = [m for m in fields_named(False) if m[0] != name]
            closing = ", ".join([f"{ov[name].label or name}: {iso}", *(f"{fl}: {fs}" for _, _, fl, fs in also)])
            _intent.preset_call(f"{thread_id}-{fid}"[:100], "propose_changes",
                                {"changes": [{"name": name, "value": iso}, *({"name": n, "value": v} for n, v, _, _ in also)]},
                                "" if tail else closing + ".", _intent.APPLIED)
            if tail:
                self.__dict__.setdefault("_mixed", {})[thread_id] = f"set {closing}"
            out = {"kind": "value"}
        else:
            command, kind = picks.get("is_command"), picks.get("kind")
            hand_on, move, more = picks.get("needs_agent"), picks.get("asks_move"), picks.get("asks_more")
            ordered = bool(command and command.id == "yes" and kind and kind.id in ("go_to", "show", "set_value"))
            moves = bool(move and move.id == "yes") or (ordered and kind.id in ("go_to", "show"))
            # the owner (2026-11-17): what the chooser is sure of is applied; whatever else the line holds (a question,
            # an explanation, a text to write) is the agent's, which is told what was done already
            # how sure "the line asks more" must be: on the owner's recorded lines a plain "can you open X" scored 0.56
            # and 0.61, a command with a question 0.79, a text to write 0.95. Four lines, not a calibration: the QA
            # Lead's measurement sets it (INTENT_TAIL)
            tail = bool(more and more.id == "yes" and more.confidence >= float(os.environ.get("INTENT_TAIL", "0.7"))) or named
            # several sections of the form on the screen in one line: all of them opened, one line naming them
            # "the line itself says it" can be checked only when the line is in the labels' language; in another
            # language (QA, 2026-11-17: only English lines opened several) the chooser's answer stands alone
            same_tongue = ov is None or (detect(message) or "en") == (detect(" ".join(str(ov[n.name].label or "") for n in lay.nodes.values() if ov.get(n.name) is not None)[:600]) or "en")
            opens = [(k[2:], str(ov[k[2:]].label)) for k, p in picks.items()
                     if k.startswith("s:") and ov is not None and p.id == "yes" and p.confidence >= 0.8
                     and (not same_tongue or _intent.said_in(str(ov[k[2:]].label), message))]
            every = picks.get("all_sections")
            # "all the sections" of a place other than the one on the screen, which the chooser could not point at:
            # the layer does not open what is on the screen instead
            other = picks.get("other_place")
            elsewhere = bool(other and other.id == "yes")
            if every and every.id == "yes" and every.confidence >= 0.8 and ov is None:
                # every part of a page of the site (all the questions of the FAQ): of the page the line names, else this one
                t0 = picks.get("target")
                path = t0.id.partition(":")[2].partition("#")[0] if t0 and t0.id.startswith(("screen:", "part:")) else (here.path if here else "")
                page = self.site.page(path) or here
                parts = [x for x in (page.parts if page else []) if x.kind in ("accordion", "section")]
                if elsewhere and not (t0 and t0.id.startswith(("screen:", "part:"))):
                    return None                       # the line names a place the layer did not resolve: the agent's
                what = ("all", page.path if page else "")
                if len(parts) >= 2 and not _intent.has_date(message) and not self._again(thread_id, what):
                    moves_ = [{"path": page.path, ("tab" if x.kind == "accordion" else "section"): x.id} for x in parts]
                    stats.fast["handled"] = True
                    from .. import voice
                    voice.hush(thread_id)
                    return {"kind": "show", "args": moves_[0], "more": moves_[1:],
                            "title": f"{page.title}: {len(parts)} sections open" if len(parts) > 4 else ", ".join(x.title for x in parts)}
                return None                           # "all" asked and the layer cannot do all of it: the agent's turn
            if every and every.id == "yes" and every.confidence >= 0.8 and ov is not None:
                # "all the sections of the applicant tab": every section of the tab the line names, else of the open one
                t0 = picks.get("target")
                tab = t0.id.rpartition(":")[2] if t0 and t0.id.startswith(f"form:{here.path if here else ''}:") else ""
                tab = tab if tab in lay.nodes and lay.nodes[tab].role in ("tab", "step") else ""
                opens = [(n.name, str(ov[n.name].label)) for n in lay.nodes.values()
                         if n.role in ("accordion", "section") and n.name and ov.get(n.name) is not None and ov[n.name].visible
                         and ov[n.name].label and (n.parent == tab if tab else n.parent in wide.on_screen)][:12]
                # QA (2026-11-17, "In contract step open all sections"): the line names a step the layer did not
                # resolve, and it opened the tab on the screen with confidence. Words beside "all the sections" and
                # the tab's own name mean a place is named: the agent's turn, which asks which one
                if elsewhere and not tab:
                    return None
            if every and every.id == "yes" and every.confidence >= 0.8 and len(opens) < 2:
                return None                           # "all" asked and the layer cannot name them: the agent's turn
            if len(opens) >= 2 and not _intent.has_date(message):
                if self._again(thread_id, ("open", tuple(n for n, _ in opens))):
                    stats.trace["why"] = "repeat"
                    return None
                closing = ", ".join(label for _, label in opens) + "."
                _intent.preset_calls(f"{thread_id}-{fid}"[:100], [("focus_field", {"name": n}) for n, _ in opens],
                                     "" if tail else closing)
                stats.fast["handled"] = True
                if tail:
                    self.__dict__.setdefault("_mixed", {})[thread_id] = f"opened {closing[:-1]}"
                else:
                    from .. import voice
                    voice.hush(thread_id)
                return {"kind": "focus"}
            value, target = picks.get("value") if ov is not None else None, picks.get("target")
            # a line that is nothing but a value of the form on the screen ("Gender: Male", "male"): the chooser is
            # very sure of the option and the line asks nothing else. It need not sound like a command
            # ... and the option itself is said in the line: with the conversation in its state the chooser may name
            # the value of an earlier message for a line that is about something else (a check after its pick)
            said = False
            if value:
                e0 = ov.get(value.id.partition("=")[0])
                opt0 = value.id.partition("=")[2]
                shown0 = next((str(o.get("name")) for o in (e0.options or []) if str(o.get("id")) == opt0), "") if e0 is not None else ""
                said = bool(shown0) and _intent.said_in(shown0, message)
            # several values in one line: every field of the screen the chooser is sure of (0.8), whose field or
            # option the line itself says; all of them on one card of the form, applied with Undo. When the line
            # asks more, the form's own model goes on after the card and knows what is done
            many = fields_named(moves)
            if many and not (kind and kind.id in ("question", "other")):
                closing = ", ".join(f"{fl}: {fs}" for _, _, fl, fs in many) + "."
                _intent.preset_call(f"{thread_id}-{fid}"[:100], "propose_changes",
                                    {"changes": [{"name": n, "value": v} for n, v, _, _ in many]},
                                    "" if tail else closing, _intent.APPLIED)
                stats.fast["handled"] = True
                stats.fast["set"] = closing
                if tail:
                    self.__dict__.setdefault("_mixed", {})[thread_id] = f"set {closing[:-1]}"
                if not tail:
                    from .. import voice
                    voice.hush(thread_id)
                return {"kind": "value"}
            bare = bool(value and said and value.confidence >= 0.9 and not moves and not tail
                        and not (more and more.id == "yes") and not (kind and kind.id in ("question", "other")))
            if not ordered and not moves and not bare:
                stats.trace["why"] = stats.trace["why"] or "not_an_order"
                return None                           # not the person's order: the agent's turn
            if bare or (ordered and (kind.id == "set_value" or (value and not target))):
                if value and not tail:                # a value with more to answer: the form's assistant does both
                    name, _, opt = value.id.partition("=")
                    e = ov.get(name)
                    if e is not None and e.editable:
                        is_bool = e.node.role == "bool"
                        shown = "yes" if is_bool else next((str(o.get("name")) for o in e.options or [] if str(o.get("id")) == opt), opt)
                        _intent.preset(f"{thread_id}-{fid}"[:100], name, True if is_bool else opt, e.label or name, shown)
                        out = {"kind": "value"}
            elif target and not _intent.has_date(message):
                label = next(o.label for o in targets if o.id == target.id).split(" \u203a ")[-1]
                kind_, _, ref = target.id.partition(":")
                if kind_ == "form":
                    path, _, node = ref.partition(":")
                    page = self.site.page(path)
                    pfid = str(page.form)
                    # the form's own "show where" step, chosen here, carried out by the form: on another page when
                    # that page has loaded its form, so its live state is checked there
                    _intent.preset_call(f"{thread_id}-{pfid}"[:100], "focus_field", {"name": node}, f"{label}.")
                    if tail and here and page.path == here.path:
                        _intent.clear_preset(f"{thread_id}-{pfid}"[:100])   # with more to answer the form's assistant does both
                    elif here and page.path == here.path and ov is not None:
                        out = {"kind": "focus"}
                    else:
                        self._keep_note(thread_id, pfid, f"Show {label}. " + self._said_before(thread_id, pfid), detect(message) or "")
                        out = {"kind": "navigate", "args": {"path": page.path}, "title": page.title, "form_id": pfid}
                        # the section opens in the page's own run: the label is said there, with the model's part if any
                        self.__dict__.setdefault("_mixed", {})[thread_id] = f"opened {page.title} \u203a {label}"
                else:
                    path, _, pid = ref.partition("#")
                    page = self.site.page(path)
                    part = page.part(pid) if page and pid else None
                    args = {"path": path, **({("tab" if part.kind in ("tab", "accordion") else "section"): pid} if part else {})}
                    if agent.directive(self.site, args)[1] is not None:   # a place that is not there is the agent's to say
                        out = {"kind": "show" if part else "navigate", "args": args, "title": label}
                        before = self._said_before(thread_id, str(page.form)) if page and page.form and not (here and here.path == page.path) else ""
                        if before:
                            # what the person said elsewhere goes with them to this page's form, as the agent's own
                            # move would have noted it (QA, 2026-11-17: after a move by the layer the form knew nothing)
                            self._keep_note(thread_id, str(page.form), before, detect(message) or "")
                            out["form_id"] = str(page.form)
        if out and out["kind"] in ("navigate", "show", "focus") and self._again(
                thread_id, (out["kind"], json.dumps(out.get("args"), sort_keys=True), picks["target"].id if picks.get("target") else "")):
            stats.trace["why"] = "repeat"
            return None
        if out:
            stats.fast["handled"] = True
            if tail and out["kind"] in ("navigate", "show") and not named and not _intent.names_more(message, " ".join(
                    o.label for o in targets if o.id == (picks["target"].id if picks.get("target") else ""))):
                tail = False                          # nothing is said beside the place and the order itself
            if tail and out["kind"] in ("navigate", "show"):
                out["tail"] = True                    # the rest of the line goes on to the agent, in the same run
                stats.fast["did"] = out["title"]
            else:
                from .. import voice
                voice.hush(thread_id)   # in a talking conversation: done already, so no "let me check" before the answer
            return out
        return {"kind": "agent", "mode": "site"} if picks.get("kind") and picks["kind"].id in ("go_to", "show") else None

    def _said_before(self, thread_id: str, form_id: str) -> str:
        """The person's recent own lines on the site that this form has not seen (said on another page or to
        another form), for the hand-over note; "" when there are none. Lines the layer itself carried out as a
        move are left out: they were orders to go somewhere, not something to fill in."""
        lines = [str(e.get("text") or "").strip() for e in self.forms.transcripts.list(thread_id)
                 if e["kind"] == "user" and not e.get("layer") and e.get("form_id") != form_id and str(e.get("text") or "").strip()][-4:]
        if not lines:
            return ""
        said = " | ".join(f'"{x[:300]}"' for x in lines)
        return ("Before coming here the person said, in their own words (some of it may be meant for this form: use what "
                f"fits its fields, leave the rest, and do not ask again for what is said here): {said}")

    def _again(self, thread_id: str, what: Any) -> bool:
        """Whether the layer did this very thing for the person's previous line, a moment ago. Asked again, the
        same answer is a miss (the owner, 2026-11-17: "open all the sections" answered twice with the tab's
        name): the agent takes the line instead."""
        last = self.__dict__.setdefault("_did", {})
        before = last.get(thread_id)
        now = RunStats.now()
        last[thread_id] = (what, now)
        return bool(before and before[0] == what and now - before[1] < 120)

    async def _form_tree(self, form_id: str) -> list[tuple[str, str, list[str]]]:
        """A form's tabs, steps and sections as the server knows them without the page: (name, label, the labels
        above it). From the host's `form_for`, so the starting state; kept once per form."""
        cache = self.__dict__.setdefault("_trees", {})
        if form_id not in cache:
            tree: list[tuple[str, str, list[str]]] = []
            try:
                form = await maybe_await(self.form_for(form_id, None)) if self.form_for else None
                lay = self.forms.layout((form or {}).get("jsx_hash", "")) if form else None
                tree = self._tree_of(form) if form else []
            except Exception:  # noqa: BLE001 - a form the server cannot read has no parts to name
                tree = []
            cache[form_id] = tree
        return cache[form_id]

    def _tree_of(self, form: dict[str, Any], seen_only: bool = False) -> list[tuple[str, str, list[str]]]:
        """(name, label, the labels above it) for a form state's tabs, steps and sections. `seen_only`: the form
        on the screen, where a part the person cannot see is not something to open."""
        from ..form.overlay import Overlay
        lay = self.forms.layout(form.get("jsx_hash", ""))
        if lay is None:
            return []
        ov = Overlay(lay, form["config"], self.forms.packs.get(form.get("form_id")).pii)
        tree = []
        for node in lay.nodes.values():
            e = ov.get(node.name)
            label = (e.label if e is not None else None) or node.text
            if node.role in ("tab", "accordion", "section") and node.name and label and not (seen_only and e is not None and not e.visible):
                ups = [str(ov[x.name].label) for x in lay.ancestors(node.name) if ov.get(x.name) is not None and ov[x.name].label]
                tree.append((node.name, str(label), ups))
        return tree

    async def _named(self, thread_id: str, message: str, state: dict[str, Any], here: Any, stats: RunStats) -> dict[str, Any] | None:
        """A direct command or a request that names an object of the site by its place in the hierarchy (the
        owner, 2026-11-17: "we know the hierarchy ... the whole way down to what is opened"): a page; a tab or a
        section of any page; a tab, a step or a section of a form, on this page or on another. Decided in code
        from the names said; the way to the object may be said too ("apply for loan, application, personal
        details"). Carried out step by step: the page, then the part."""
        from .. import intent as _intent
        if not (_intent.is_direct(message) or _intent.asks_for(message)) or _intent.has_date(message):
            return None
        targets: list[dict[str, Any]] = []
        for p in self.site.pages:
            on = bool(here and p.path == here.path)
            way = [p.title, *p.keywords]
            if not on:
                targets.append({"id": p.path, "label": p.title, "kind": "page", "up": list(p.keywords)})
            targets += [{"id": f"{p.path}#{x.id}", "label": x.title, "kind": "part", "up": way, "here": on} for x in p.parts]
            if p.form:
                live = state.get("form") if on and isinstance(state.get("form"), dict) and (state.get("form") or {}).get("config") else None
                try:   # the form on the screen as it is now; any other form as the server knows it from the start
                    tree = self._tree_of(live, seen_only=True) if live else await self._form_tree(p.form)
                except Exception:  # noqa: BLE001
                    tree = []
                targets += [{"id": f"form:{p.path}:{name}", "label": label, "kind": "form", "up": [*ups, *way], "here": on}
                            for name, label, ups in tree]
        hit = _intent.match_path(message, targets)
        if not hit:
            return None
        tid, how = hit
        label = next(t["label"] for t in targets if t["id"] == tid)
        by = "the name said" if how == "said" else "a name heard nearly right"
        if tid.startswith("form:"):
            _f, path, node = tid.split(":", 2)
            page = self.site.page(path)
            fid = str(page.form)
            # the form's own "show where" step, decided here: no model. On another page it runs when that page
            # has loaded its form (the hand-off run), so the live state is checked there, not guessed here
            _intent.preset_call(f"{thread_id}-{fid}"[:100], "focus_field", {"name": node}, f"{label}.")
            if here and page.path == here.path and state.get("form"):
                out: dict[str, Any] = {"kind": "focus"}
            else:
                from ..language import detect
                self._keep_note(thread_id, fid, f"Show {label}.", detect(message) or "")
                out = {"kind": "navigate", "args": {"path": page.path}, "title": page.title, "form_id": fid}
                by += ": the page, then the section"
        else:
            path, _, pid = tid.partition("#")
            page = self.site.page(path)
            part = page.part(pid) if page and pid else None
            args = {"path": path, **({("tab" if part.kind in ("tab", "accordion") else "section"): pid} if part else {})}
            if agent.directive(self.site, args)[1] is None:
                return None
            out = {"kind": "show" if part else "navigate", "args": args, "title": part.title if part else page.title}
        stats.fast = {"ms": 0, "handled": True, "by": by}
        from .. import voice
        voice.hush(thread_id)
        return out

    def _bare_value(self, thread_id: str, message: str, state: dict[str, Any], stats: RunStats) -> dict[str, Any] | None:
        """A value said with no verb, where what is on the screen says which field it is for (the owner: the layer
        "must know which page is active, what I see, what I say"). A whole date, with the date field that has the
        focus, or the only date field of the section that is open: it goes into that field through the form's own
        card, so the form's checks and Undo apply. Two date fields in sight, none, or no form: the agent's line."""
        from .. import intent as _intent
        iso = _intent.spoken_date(message)
        form = state.get("form") or None
        if not iso or not isinstance(form, dict) or not form.get("config"):
            return None
        try:
            from ..form.overlay import Overlay
            lay = self.forms.layout(form.get("jsx_hash", ""))
            ov = Overlay(lay, form["config"], self.forms.packs.get(form.get("form_id")).pii)
        except Exception:  # noqa: BLE001
            return None
        ui = form.get("ui") or {}
        dates = [n for n in lay.fields() if n.role == "date" and ov[n.name].editable]
        focused = next((n for n in dates if n.name == ui.get("focused")), None)
        opened = set(ui.get("openAccordions") or [])
        in_sight = [n for n in dates if any(x.name in opened for x in lay.ancestors(n.name))]
        field = focused or (in_sight[0] if len(in_sight) == 1 else None)
        if field is None:
            return None
        fid = str(form.get("form_id") or "form")
        label = ov[field.name].label or field.name
        _intent.preset(f"{thread_id}-{fid}"[:100], field.name, iso, label, iso)
        stats.fast = {"ms": 0, "handled": True, "by": "a date for the date field in sight"}
        from .. import voice
        voice.hush(thread_id)
        return {"kind": "value"}

    def _taken_up(self, thread_id: str, message: str, stats: RunStats) -> dict[str, Any] | None:
        """The last answer offered to open a page or start a form, and this line only takes that up ("open it",
        "yes please", "that one"): carried out in code, at once. The person agreed to exactly what was offered;
        a model turn would only make them wait."""
        from .. import intent as _intent
        off = self._offers.get(thread_id)
        if os.environ.get("INTENT_CODE") != "1" or not isinstance(off, dict) or not _intent.takes_up(message):
            return None
        args = dict(off.get("args") or {})
        if off.get("tool") == "open_form":
            page = self.site.form_page(str(args.get("form_id") or ""))
            if not page:
                return None
            # the form's page opens now; the form's assistant takes over there, as after any hand-off
            self._keep_note(thread_id, page.form or "", str(args.get("note") or "").strip()[:600],
                            str(args.get("language") or "").strip()[:40])
            out = {"kind": "navigate", "args": {"path": page.path}, "title": page.title, "form_id": page.form}
        else:
            if agent.directive(self.site, args)[1] is None:
                return None
            out = {"kind": "navigate", "args": args, "title": str(off.get("title") or "")}
        self._offers.pop(thread_id, None)
        stats.fast = {"ms": 0, "handled": True, "by": "the offer taken up"}
        from .. import voice
        voice.hush(thread_id)
        return out

    def _chooser(self, message: str, page: str):
        """The choice tool's server half for Dushes: the options are built here, from the site map as it is."""
        from .. import intent as _intent
        from ..language import detect

        async def choose(what: str, sets: list[str]) -> dict[str, Any]:
            options = []
            if "screens" in sets:
                options += [_intent.Option(f"screen:{p.path}", p.title) for p in self.site.pages]
            if "parts" in sets:
                options += [_intent.Option(f"part:{p.path}#{x.id}", f"{p.title}: {x.title}") for p in self.site.pages for x in p.parts]
            return await _intent.choose_on_screen(self.intent, what, options, detect(message) or "en", page)
        return choose

    def _titled(self, message: str, here: Any) -> Any:
        """The page (other than this one) whose whole title is said in the message, the longest such title. Articles
        do not count: "apply for loan" names "Apply for a loan"."""
        def plain(text: str) -> str:
            return " ".join(w for w in re.findall(r"\w+", (text or "").lower()) if w not in ("a", "an", "the"))
        text = f" {plain(message)} "
        hits = [p for p in self.site.pages if not (here and p.path == here.path)
                and (t := plain(p.title)) and f" {t} " in text]
        return max(hits, key=lambda p: len(p.title)) if hits else None

    def _context(self, thread_id: str, state: dict[str, Any], here: Any, ov: Any = None, lay: Any = None,
                 pack: Any = None) -> dict[str, Any]:
        """What the chooser is told beside the line, about as much as the form's own assistant is told (the owner,
        2026-11-17): the screen; the form on it, as that assistant reads it (its tabs, steps, sections and fields,
        with their kind, their options, what is required and what is filled; personal data is "<filled>", never a
        value); what the last answer offered and what was opened last; and the last ten messages of the
        conversation, both sides. Every piece goes through the filter before it leaves (`safe_context`)."""
        out: dict[str, Any] = {"page": here.title if here else ""}
        if ov is not None:
            try:
                from ..form.render import locate, render_focus, render_outline
                ui = (state.get("form") or {}).get("ui") or {}
                loc = locate(ov, ui)
                deps = self.forms.deps(lay.jsx_hash)
                label = lambda name: (ov.get(name).label if ov.get(name) is not None else None) or ""  # noqa: E731
                out["open_sections"] = [label(n) for n in ui.get("openAccordions") or [] if label(n)]
                out["field_in_focus"] = label(ui.get("focused") or "")
                out["form"] = render_outline(ov, loc, deps, pack, 0) + "\n\n" + render_focus(ov, loc, deps, pack)
            except Exception:  # noqa: BLE001 - a form that cannot be rendered adds nothing
                pass
        off = self._offers.get(thread_id)
        if isinstance(off, dict):
            out["offered"] = [str(off.get("title") or "")]            # the target, not the assistant's sentence
        out["opened_last"] = self.__dict__.setdefault("_last", {}).get(thread_id, "")
        turns = [e for e in self.forms.transcripts.list(thread_id) if e["kind"] in ("user", "assistant") and e.get("text")]
        out["last_messages"] = [("person: " if e["kind"] == "user" else "assistant: ") + str(e["text"]) for e in turns[-10:]]
        return out

    async def _fast_move(self, thread_id: str, message: str, run_id: str, fast: dict[str, Any],
                         reply_to: list[dict[str, Any]] | None) -> AsyncIterator[dict]:
        """A move the layer picked, as the run Dushes would have made: the same directive, one line of text."""
        result, d = agent.directive(self.site, fast["args"])
        if d and fast.get("form_id"):
            d = {**d, "form_id": fast["form_id"]}   # a form's page: the client starts the hand-off there
        tx = self.forms.transcripts
        tx.append(thread_id, new_entry("user", text=message, layer=True, **({"reply_to": as_list(reply_to)} if reply_to else {})))
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
        self.__dict__.setdefault("_last", {})[thread_id] = fast["title"]   # for "and now ..." on the next line
        mid, text = f"msg_{uuid.uuid4().hex[:12]}", f"{fast['title']}."
        yield {"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"}
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": text}
        yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
        tx.append(thread_id, new_entry("assistant", text=text, message_id=mid))
        if d:
            yield {"type": "CUSTOM", "name": "site_directive", "value": d}
        for extra in fast.get("more") or []:          # every other part of "open all of them"
            more = agent.directive(self.site, extra)[1]
            if more:
                yield {"type": "CUSTOM", "name": "site_directive", "value": more}
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}

    async def _site_turn(self, thread_id: str, message: str | None, state: dict[str, Any], run_id: str,
                         host: Any, form_kwargs: dict[str, Any], recorded: bool = False,
                         reply_to: list[dict[str, Any]] | None = None,
                         stats: RunStats | None = None, done: str = "") -> AsyncIterator[dict]:
        """Dushes' turn (and a same-run hand-off to a form). `done`: what the choice layer carried out for this
        message already (its line is the last in the transcript). `recorded`: the user's message is already in
        the transcript (the form agent gave it back)."""
        tx = self.forms.transcripts
        history = [("user" if e["kind"] == "card_result" else e["kind"], e.get("text", "")) for e in tx.list(thread_id)
                   if e["kind"] in ("user", "assistant", "card_result")][-self.history:] if self.history > 0 else []
        if done and len(history) >= 2 and history[-1][0] == "assistant" and history[-2][0] == "user":
            history = history[:-2]   # the message and the layer's line: the message goes last, the line is in `done`
        if recorded and history and history[-1][0] == "user":
            history = history[:-1]   # the message itself goes last, not twice
        if message and not recorded:
            tx.append(thread_id, new_entry("user", text=message, **({"reply_to": as_list(reply_to)} if reply_to else {})))
        from ..reply import quoted, resolve
        heard = resolve(reply_to, tx.list(thread_id))
        said: list[str] = []
        page = ((state.get("page") or {}).get("path")) or "/"
        ctx = SiteRunCtx(thread_id=thread_id, page=page, state=state, message=message or "", host=host)
        live = ""
        if self.context:
            try:
                live = str(await maybe_await(self.context(ctx)) or "")
            except Exception:  # noqa: BLE001 — the turn goes on without the host's facts
                log.exception("site context failed")
        if done:
            live = f"{live}\n{done}".strip()
        handed: dict[str, Any] = {}

        async def keep(form_id: str, note: str, language: str = "") -> bool:
            """The note for the form; True when the form agent answers now, in this run (form_for built it)."""
            form = None
            if self.form_for:
                try:
                    form = await maybe_await(self.form_for(form_id, ctx))
                except Exception:  # noqa: BLE001 — fall back to the page's hand-off run
                    log.exception("form_for failed")
            self._keep_note(thread_id, form_id, note, language, status="used" if form else "pending")
            if form:
                handed.update(form_id=form_id, note=note, language=language, form=form)
            return bool(form)

        back: dict[str, str] = {}   # to_form was called: the form agent answers this message next

        def to_form(reason: str) -> None:
            back["reason"] = reason

        # on a form page Dushes can give a form question to the form agent, unless the form agent just gave it back
        give = to_form if state.get("form") and message and not recorded else None
        has_docs = bool(self.forms.knowledge.documents_for(SCOPE))
        failed = False
        first_mid = None
        from .. import intent as _intent_mod
        from .. import voice
        aloud = voice.active(thread_id)   # a voice conversation speaks this thread's answers: short, and no chips
        async for ev in agent.answer(self.model or self.forms.models.agent, self.site, voice.heard_as(quoted(message, heard) or "", aloud) or "", history, page,
                                     thread_id, run_id, keep, doc_passages=self.doc_passages(message or "") if has_docs else "",
                                     ask_docs=self._ask_documents if has_docs else None, live=live,
                                     instructions=self.instructions, style=self.style, tools=self.tools, ctx=ctx,
                                     suggestions=self.suggestions and not aloud, finish=False,
                                     stay_on_form=self._filling(thread_id, state), to_form=give, stats=stats,
                                     asked=message, offered=self._offers.pop(thread_id, False), upfront=aloud,
                                     chooser=self._chooser(message or "", page) if self.intent.on and os.environ.get("INTENT_TOOL", "1") == "1" else None,
                                     # a direct command or a plain request that the model carries out with its own
                                     # tool ends there: one short line, no description and no question back
                                     end_on_move=os.environ.get("INTENT_END_ON_MOVE") == "1" or (
                                         self.intent.on and bool(message) and (
                                             _intent_mod.is_direct(message) or _intent_mod.asks_for(message))
                                         and not message.rstrip().endswith("?"))):
            if ev["type"] == "CUSTOM" and ev.get("name") == "site_offer":
                while len(self._offers) >= 5000:
                    self._offers.pop(next(iter(self._offers)))
                self._offers[thread_id] = dict(ev.get("value") or {}) or True   # the next message may take it up
            if ev["type"] == "TEXT_MESSAGE_CONTENT":
                said.append(ev["delta"])
                first_mid = first_mid or ev.get("messageId")
            elif ev["type"] == "RUN_ERROR":
                failed = True
            yield ev
        if not failed and "".join(said).rstrip().endswith("?"):   # an offer made in words alone ("Want me to open it?")
            while len(self._offers) >= 5000:
                self._offers.pop(next(iter(self._offers)))
            self._offers.setdefault(thread_id, True)   # a plain yes to the closing question may open what it names
            # (an offer the server recorded with its target, a moment ago in this turn, is kept as it is)
        if said:
            tx.append(thread_id, new_entry("assistant", text="".join(said), **({"message_id": first_mid} if first_mid else {})))
        if failed:
            return
        if back and not handed:   # the form agent answers the message itself, in this run (no hand_back now)
            form = self._with_page(state["form"], state)
            fid = str(form.get("form_id") or "form")
            form_thread = f"{thread_id}-{fid}"[:100]
            out = Said()
            again = None
            kw = {**form_kwargs, "capabilities": with_hand_back(form_kwargs.get("capabilities"))}   # one tool list per thread
            async for ev in self.forms.run(form_thread, message=message, state=form, run_id=run_id,
                                           **({"reply_to": as_list(reply_to)} if reply_to else {}), **kw):
                if ev["type"] == "CUSTOM" and ev.get("name") == "hand_back":
                    again = ev.get("value") or {}
                    continue
                if ev["type"] == "RUN_STARTED" or again is not None:
                    continue
                out.see(ev)
                yield ev
            if out.text().strip():
                tx.append(thread_id, new_entry("assistant", text=out.text(), form_id=fid, **out.first_id()))
            for card in out.cards:
                tx.append(thread_id, new_entry("display", card=card, form_id=fid))
            if again is not None:   # the form gave it back: Dushes answers itself (recorded: no to_form now)
                async for ev in self._site_turn(thread_id, message, state, run_id, host, form_kwargs, recorded=True,
                                                reply_to=reply_to, stats=stats):
                    if ev["type"] != "RUN_STARTED":
                        yield ev
                return
            return
        if not handed:
            yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}
            return
        # the form agent answers now, in this same run: its words and cards follow Dushes' open_form
        fid, form = handed["form_id"], self._with_page(handed["form"], state, handed["form_id"])
        form_thread = f"{thread_id}-{fid}"[:100]
        out = Said()
        kw = {**form_kwargs, "capabilities": with_hand_back(form_kwargs.get("capabilities"))}   # one tool list per thread
        async for ev in self.forms.run(form_thread, message=handoff_message(handed["note"], handed["language"]),
                                       state=form, run_id=run_id, **kw):
            if ev["type"] == "CUSTOM" and ev.get("name") == "hand_back":
                continue   # just handed over: the form agent answers this one
            if ev["type"] == "RUN_STARTED":
                continue
            out.see(ev)
            yield ev
        if out.text().strip():
            tx.append(thread_id, new_entry("assistant", text=out.text(), form_id=fid, **out.first_id()))
        for card in out.cards:
            tx.append(thread_id, new_entry("display", card=card, form_id=fid))


def create_dushes_router(site: Dushes, host: Any = None):
    """FastAPI router: POST /run (AG-UI RunAgentInput; state {page, form?}), GET /map (the site map for the page).
    `host(request)` (sync or async) builds the host's object for each run: SiteRunCtx.host in every callback."""
    from fastapi import APIRouter, HTTPException
    from pydantic import ValidationError

    from .. import agui, voice

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

    @r.post("/transcribe")
    async def transcribe(file: UploadFile = File(...), language: str | None = Form(None)) -> dict:
        """Dictation for the site chat: the form guide's transcription."""
        from ..server import transcribe_upload
        started = RunStats.now()
        out = await transcribe_upload(site.forms, file, language)
        site._heard = (RunStats.now(), round((RunStats.now() - started) * 1000))   # for the demo's label
        return out

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
        if host is not None:
            kw["host"] = await maybe_await(host(request))
        from ..guide import ModelChoiceError
        try:   # before the stream starts: an unknown choice, or another model than the conversation's
            site.forms.check_model(kw["thread_id"], kw.get("model"))
        except ModelChoiceError as e:
            raise HTTPException(e.status, e.detail) from None
        enc = agui.encoder(request.headers.get("accept"))

        async def events():
            async for ev in site.run(**kw):
                voice.seen(kw["thread_id"], ev)   # a voice conversation of this thread says the answer
                yield agui.encode(ev, enc)

        return StreamingResponse(agui.alive(events(), enc), media_type=enc.get_content_type(),
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return r


# the names before Dushes, kept so existing hosts keep working
SiteGuide = Dushes
create_site_router = create_dushes_router


def _decision_trace(stats: Any, seen: dict[str, Any], run_id: str, more_to_come: bool, site: Any) -> dict[str, Any]:
    """The CUSTOM `decision_trace` event of a run in which the choice layer was asked: how the turn was decided,
    for the person's own conversation only (a host turns it on). No value of theirs is in it beyond the line as it
    left the filter and the labels of what was applied."""
    import datetime
    fast, trace = getattr(stats, "fast", None) or {}, dict(stats.trace)
    applied: list[dict[str, Any]] = []
    if fast.get("handled"):
        for item in seen.get("screen") or []:
            name, value = item.get("name"), item.get("value") or {}
            if name == "site_directive":
                page = site.page(str(value.get("path") or ""))
                pid = value.get("tab") or value.get("section")
                part = page.part(pid) if page and pid else None
                applied.append({"what": "open", "target": f"{value.get('path')}{'#' + pid if pid else ''}",
                                "label": " \u203a ".join(x for x in (page.title if page else "", part.title if part else "") if x)})
            elif name == "ui_directive" and value.get("type") == "focus":
                applied.append({"what": "open", "target": str(value.get("target")), "label": str(value.get("target"))})
            elif name == "on_interrupt" and value.get("quiet"):
                applied += [{"what": "set", "target": str(r.get("name")), "label": f"{r.get('label') or r.get('name')}: {r.get('display') or r.get('value')}"}
                            for r in value.get("changes") or [] if isinstance(r, dict)]
    tail = bool(fast.get("did")) or (bool(fast.get("handled")) and more_to_come)
    why = trace.pop("why", "")
    if not fast.get("handled"):
        to_agent: dict[str, Any] | None = {"why": "late" if fast.get("late") else why or "not_sure", "already_done": []}
    elif tail:
        to_agent = {"why": why or "asks_more", "already_done": [a["label"] for a in applied]}
    else:
        to_agent = None
    return {"run_id": run_id, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), **trace,
            "outcome": "agent" if not fast.get("handled") else "partly" if tail else "jev",
            "steps": [{"who": "jev", "title": "The choice model", "ms": fast.get("ms"), "tokens": fast.get("tokens")}],
            "applied": applied, "to_agent": to_agent}


def _demo_log(thread_id: str, message: str | None, resume: Any, handoff: bool, state: dict[str, Any] | None,
              stats: Any, seen: dict[str, Any], ended: str) -> None:
    """The local demo's record of a turn (DEMO_RUNS_DIR set; never in the package's own runs): one JSON line a
    turn in a file a day, on this machine only. Who typed: threads listed in `mine.txt` of that folder, or with
    a script's prefix, are the team's; every other thread is the owner's."""
    folder = os.environ.get("DEMO_RUNS_DIR", "")
    if not folder:
        return
    try:
        import datetime
        import pathlib
        d = pathlib.Path(folder)
        d.mkdir(parents=True, exist_ok=True)
        mine = d / "mine.txt"
        ours = set(mine.read_text().split()) if mine.exists() else set()
        team = thread_id in ours or thread_id.startswith(("replay-", "qa-", "eval-", "tl-"))
        now = datetime.datetime.now()
        fast = getattr(stats, "fast", None) or {}
        row = {"time": now.isoformat(timespec="seconds"), "thread": thread_id, "by": "team" if team else "owner",
               "page": ((state or {}).get("page") or {}).get("path"),
               "line": message, "kind": "card answer" if resume is not None else "page loaded" if handoff and not message else "line",
               "handled": seen.get("label") or "", "chooser": {k: fast.get(k) for k in ("ms", "tokens", "targets", "sure", "handled", "late", "did") if k in fast},
               "screen": seen.get("screen") or [],
               "reply": "".join(x for x in seen.get("said") or [] if not x.startswith("\u2014 ")),
               "seconds": round(RunStats.now() - stats.t0, 2), "ended": ended}
        with open(d / f"{now:%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    except Exception:  # noqa: BLE001 - the record never breaks a turn
        log.exception("demo log failed")
