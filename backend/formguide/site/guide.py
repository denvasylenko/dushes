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
        async for ev in self._run(thread_id, stats, message=message, state=state, resume=resume, run_id=run_id,
                                  handoff=handoff, host=host, reply_to=reply_to, **form_kwargs):
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
                if fast and fast.get("handled"):
                    label = f"{who} \u00b7 {fast['ms']} ms"
                elif getattr(stats, "decided", False):
                    label = who
                else:
                    name = str(_model_id(self.model or self.forms.models.agent))
                    took = RunStats.now() - stats.t0
                    why = f"no answer within {self.intent.settings.timeout_ms} ms" if fast and fast.get("late") else "not sure"
                    asked = f" (after {who} {fast['ms']} ms: {why})" if fast else ""
                    label = f"{'Haiku' if 'haiku' in name.lower() else name} \u00b7 {took:.1f} s{asked}"
                heard = getattr(self, "_heard", None)
                if heard and RunStats.now() - heard[0] < 30:   # this line was dictated: how long the speech took to read
                    label = f"heard in {heard[1]} ms \u00b7 {label}"
                    self._heard = None
                lid = f"label_{uuid.uuid4().hex[:10]}"
                yield {"type": "TEXT_MESSAGE_START", "messageId": lid, "role": "assistant"}
                yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": lid, "delta": f"\u2014 {label}"}
                yield {"type": "TEXT_MESSAGE_END", "messageId": lid}
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
        if resume is not None and _intent.has_preset(form_thread0):
            stats.decided = True                     # the closing line of a value the layer picked
        elif message:
            _intent.clear_preset(form_thread0)        # a new message: nothing decided is left over
        fast = await self._fast(thread_id, message, state, stats) if message and resume is None and not handoff else None
        if fast and fast["kind"] in ("navigate", "show"):
            async for ev in self._fast_move(thread_id, message, run_id, fast, reply_to):
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
        """Ask the choice layer about the phrase: one call, every question. A dict when it is a command the layer
        may carry out by itself (a screen, a part of this screen, a value named outright); None for the agent."""
        from .. import intent as _intent
        from ..language import detect
        layer = self.intent
        if not layer.on:
            return None   # (a talking conversation goes through the layer too: what was heard is an ordinary line)
        here = self.site.page(((state.get("page") or {}).get("path")) or "")
        if not _intent.is_direct(message):
            # not a direct command (no verb of the short list at its start, or a question): the layer is not asked
            # at all. The line is the model's, which has the choice tool; a page said by its whole title makes it
            # the site agent's turn
            return {"kind": "agent", "mode": "site"} if self._titled(message, here) else None
        # the questions and the order of the decision are the QA Lead's wrapper, as it measured on her fifth set
        qs: dict[str, Any] = {
            "is_command": _intent.command_question(),
            "kind": _intent.Question("choice", "turn", "What kind of line is it?", (
                _intent.Option("go_to", "an order to go to a section or open an item"),
                _intent.Option("show", "an order to highlight, scroll to or point at something"),
                _intent.Option("set_value", "an order to set a value the line names outright"),
                _intent.Option("question", "where, how, why, what, can I"),
                _intent.Option("other", "a text to write, a judgement or a suggestion"))),
            "needs_agent": _intent.Question("noul", "needs_agent", "Does the line name a person or a company that is not "
                                            "on the screen, ask a question, ask for a text, or need judgement?"),
            "section": _intent.screen_question(self.site)}
        qs["names_part"] = _intent.Question("noul", "names_part", "Does the line name a specific part inside a page "
                                            "(a tab, a section, a block, a field), and not only the page itself?")
        if any(p.parts for p in self.site.pages):
            qs["element"] = _intent.parts_question(self.site)
        form, ov = state.get("form") or None, None
        if isinstance(form, dict) and form.get("config"):
            try:
                from ..form.overlay import Overlay
                lay = self.forms.layout(form.get("jsx_hash", ""))
                pack = self.forms.packs.get(form.get("form_id"))
                ov = Overlay(lay, form["config"], pack.pii) if lay is not None else None
                vq = _intent.value_question(ov, set(pack.consents or {})) if ov is not None else None
                if vq:
                    qs["value"] = vq
                fq = _intent.form_part_question(ov) if ov is not None else None
                if fq:
                    qs["form_part"] = fq
            except Exception:  # noqa: BLE001 - a form the layer cannot read is the agent's
                ov = None
        # in code, before anything is sent: a date is never a place to go, and a name the screen does not show is
        # the agent's (the CPO's two rules)
        shown = [p.title for p in self.site.pages] + [x.title for p in self.site.pages for x in p.parts]
        for name in ("value", "form_part"):
            if name in qs:
                shown += [o.label for o in qs[name].options]
        if _intent.has_date(message) or _intent.names_off_screen(message, shown):
            return None
        started = RunStats.now()
        picks = await layer.pick_many(message, detect(message) or "en", qs, here.path if here else "")
        ms = round((RunStats.now() - started) * 1000)
        stats.fast = {"ms": ms, "handled": False, "late": not picks and ms >= layer.settings.timeout_ms - 10}
        # the demo's terminal shows what the layer was sure of (ids and confidences only, never the phrase)
        log.warning("choice layer: %d ms, asked %s, sure of %s", ms, sorted(qs),
                    {k: (v.id, round(v.confidence, 2)) for k, v in picks.items()})
        # a page of the site named by its whole title ("car insurance") is the site's business wherever the person
        # is: inside a form too. It is never the form agent's "there is no such section here"
        titled = self._titled(message, here)
        to_site = {"kind": "agent", "mode": "site"} if titled else None
        if (titled and agent.wants_to_go(message) and not ("names_part" in picks and picks["names_part"].id == "yes")
                and not _intent.names_more(message, f"{titled.title} {' '.join(titled.keywords)}")):
            # a direct request ("can you open car insurance") for a page said by its whole title: the package's own
            # rule for a direct request settles it, whatever the chooser made of the polite form
            stats.fast["handled"] = True
            return {"kind": "navigate", "args": {"path": titled.path}, "title": titled.title}
        command, kind = picks.get("is_command"), picks.get("kind")
        if not command or command.id != "yes" or not kind or kind.id not in ("go_to", "show", "set_value"):
            return to_site                            # not an order, or a question: the agent; a question never jumps
        hand_on = picks.get("needs_agent")
        if hand_on and hand_on.id == "yes" and hand_on.confidence >= 0.6:
            return to_site
        page = self.site.page(picks["section"].id) if "section" in picks else None
        if page and here and page.path == here.path:
            page = None                               # the screen the person is on is not a place to go
        if kind.id != "set_value" and not page:
            page = titled                             # the chooser was torn between two pages; the title is said outright
        ppage, part = None, None                      # a part of a page of the site
        if "element" in picks:
            path, _, pid = picks["element"].id.partition("#")
            ppage = self.site.page(path)
            part = ppage.part(pid) if ppage else None
            if part and not _intent.said_in(part.title, message):
                ppage, part = None, None              # the nearest part, not the one that was said
        names_part = "names_part" in picks and picks["names_part"].id == "yes"
        if page and not part and _intent.names_more(message, f"{page.title} {' '.join(page.keywords)}"):
            names_part = True                         # the line says more than the page: a part of it is meant
        value = picks.get("value") if ov is not None else None
        form_part = picks.get("form_part") if ov is not None else None
        if form_part and not _intent.said_in(next((o.label for o in qs["form_part"].options if o.id == form_part.id), ""), message):
            form_part = None
        out: dict[str, Any] | None = None
        if kind.id == "set_value" or (not page and not part and not form_part and value):
            # "select the terrace" may come as an order to go: with no place named and a value named, it is a value
            if value and not (kind.id != "set_value" and (page or part)):
                name, _, opt = value.id.partition("=")
                e = ov.get(name)
                if e is not None and e.editable:
                    is_bool = e.node.role == "bool"
                    shown = "yes" if is_bool else next((str(o.get("name")) for o in e.options or [] if str(o.get("id")) == opt), opt)
                    fid = str(form.get("form_id") or "form")
                    _intent.preset(f"{thread_id}-{fid}"[:100], name, True if is_bool else opt, e.label or name, shown)
                    out = {"kind": "value"}
        elif part and (not page or page.path == ppage.path):
            key = "tab" if part.kind in ("tab", "accordion") else "section"
            out = {"kind": "show", "args": {"path": ppage.path, key: part.id}, "title": part.title}
        elif form_part and not page:
            # a tab or a section of the form on this screen: the form's own "show where" step, decided here
            label = next((o.label for o in qs["form_part"].options if o.id == form_part.id), form_part.id)
            fid = str(form.get("form_id") or "form")
            _intent.preset_call(f"{thread_id}-{fid}"[:100], "focus_field", {"name": form_part.id}, f"{label}.")
            out = {"kind": "focus"}
        elif page and not part and not names_part:
            out = {"kind": "navigate", "args": {"path": page.path}, "title": page.title}
        else:
            # an order to go or to show whose place the layer cannot open by itself (a part it does not know, two
            # places that disagree, nothing sure): Dushes looks wider. Opening the page and saying its name when a
            # part was asked for would be a false "done"
            out = {"kind": "agent", "mode": "site"}
        if out and out["kind"] in ("navigate", "show") and agent.directive(self.site, out["args"])[1] is None:
            out = None                                # the place is not there (any more): the agent says so
        if out and out["kind"] != "agent":
            stats.fast["handled"] = True
        return out or to_site

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
        """The page (other than this one) whose whole title is said in the message, the longest such title."""
        text = " " + " ".join(re.findall(r"\w+", (message or "").lower())) + " "
        hits = [p for p in self.site.pages if not (here and p.path == here.path)
                and (t := " ".join(re.findall(r"\w+", p.title.lower()))) and f" {t} " in text]
        return max(hits, key=lambda p: len(p.title)) if hits else None

    async def _fast_move(self, thread_id: str, message: str, run_id: str, fast: dict[str, Any],
                         reply_to: list[dict[str, Any]] | None) -> AsyncIterator[dict]:
        """A move the layer picked, as the run Dushes would have made: the same directive, one line of text."""
        result, d = agent.directive(self.site, fast["args"])
        tx = self.forms.transcripts
        tx.append(thread_id, new_entry("user", text=message, **({"reply_to": as_list(reply_to)} if reply_to else {})))
        yield {"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id}
        mid, text = f"msg_{uuid.uuid4().hex[:12]}", f"{fast['title']}."
        yield {"type": "TEXT_MESSAGE_START", "messageId": mid, "role": "assistant"}
        yield {"type": "TEXT_MESSAGE_CONTENT", "messageId": mid, "delta": text}
        yield {"type": "TEXT_MESSAGE_END", "messageId": mid}
        tx.append(thread_id, new_entry("assistant", text=text, message_id=mid))
        if d:
            yield {"type": "CUSTOM", "name": "site_directive", "value": d}
        yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}

    async def _site_turn(self, thread_id: str, message: str | None, state: dict[str, Any], run_id: str,
                         host: Any, form_kwargs: dict[str, Any], recorded: bool = False,
                         reply_to: list[dict[str, Any]] | None = None,
                         stats: RunStats | None = None) -> AsyncIterator[dict]:
        """Dushes' turn (and a same-run hand-off to a form). `recorded`: the user's message is already in
        the transcript (the form agent gave it back)."""
        tx = self.forms.transcripts
        history = [("user" if e["kind"] == "card_result" else e["kind"], e.get("text", "")) for e in tx.list(thread_id)
                   if e["kind"] in ("user", "assistant", "card_result")][-self.history:] if self.history > 0 else []
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
                                     end_on_move=os.environ.get("INTENT_END_ON_MOVE") == "1"):
            if ev["type"] == "CUSTOM" and ev.get("name") == "site_offer":
                while len(self._offers) >= 5000:
                    self._offers.pop(next(iter(self._offers)))
                self._offers[thread_id] = True   # the next message may be a plain yes to it
            if ev["type"] == "TEXT_MESSAGE_CONTENT":
                said.append(ev["delta"])
                first_mid = first_mid or ev.get("messageId")
            elif ev["type"] == "RUN_ERROR":
                failed = True
            yield ev
        if not failed and "".join(said).rstrip().endswith("?"):   # an offer made in words alone ("Want me to open it?")
            while len(self._offers) >= 5000:
                self._offers.pop(next(iter(self._offers)))
            self._offers[thread_id] = True   # a plain yes to the closing question may open what it names
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
