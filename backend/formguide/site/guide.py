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

import logging
import re
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

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


def names_a_field(text: str, form: dict[str, Any]) -> bool:
    """The message uses a word of one of the form's field labels (a stem, so "loans" matches "Loan amount" and
    other word forms of the same label match too)."""
    props = ((form or {}).get("config") or {}).get("props") or {}
    words = re.findall(r"\w+", text.lower())
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

class Dushes:
    def __init__(self, form_guide: FormGuide, site: SiteMap, model: Any = None,
                 knowledge_namespaces: list[str] | None = None, router_model: Any = None, *,
                 context: Any = None, instructions: str = "", style: str | None = None, history: int = HISTORY,
                 tools: list[SiteTool] | None = None, suggestions: bool = False, form_for: Any = None):
        self.forms = form_guide
        self.context = context            # (ctx) -> str | Awaitable[str]: live facts, in the prompt every turn
        self.instructions = instructions  # added to the site map's own instructions
        self.style = style                # replaces the default reply length rule
        self.history = history            # past turns Dushes sees
        self.tools = list(tools or [])    # the host's SiteTools
        self.suggestions = suggestions    # suggest_next -> CUSTOM suggestions
        self.form_for = form_for          # (form_id, ctx) -> form state | None: the same-run hand-off
        self.site = site
        self.model = model   # Dushes' model; default: the form guide's agent model
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
        if _NAV.search(text):
            return "site"   # an explicit move: go to, open, take me ...
        if _NAV_OTHER.search(text):
            return "unclear"   # a move in another language, or a form section: the model decides
        if _BUSINESS.search(text):
            return "unclear"   # where the business is, how to reach it: rarely the form's
        own = set(here.keywords) | {here.title.lower()} if here else set()   # the form page's own words stay with the form
        for p in self.site.pages:   # another page named by its title or keywords
            if here and p.path == here.path:
                continue
            words = [w for w in (p.title.lower(), *p.keywords) if w not in own]
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words if len(w) > 2):
                return "unclear"   # "a car loan" on the loan form is the form's; "the barbershop prices" is not
        if self._last_speaker(thread_id)[0] == "site":
            return "unclear"   # Dushes spoke last: the message may answer it
        if is_question(message) and not names_a_field(message, state.get("form") or {}):
            return "unclear"   # a question about none of this form's fields ("how many new requests?")
        return "form"

    async def classify(self, message: str, state: dict[str, Any], thread_id: str | None = None) -> str:
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
        try:
            out = await asyncio.wait_for(self.router_model.ainvoke([HumanMessage(prompt)]), timeout=4)
        except Exception as e:  # noqa: BLE001 — never block a turn on the router
            log.warning("site router failed (%s): the turn stays with the form", type(e).__name__)
            return "form"
        word = _text_of(out).strip().lower()
        log.info("site router: %r -> %s", message[:60], word[:20])
        return "site" if word.startswith("site") else "form"

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
                {"id": e["id"], "role": e["kind"], "content": e.get("text", "")}
                for e in self.forms.transcripts.list(thread_id)
                if (e["kind"] in ("user", "assistant") and e.get("text")) or (e["kind"] == "display" and e.get("card"))]
        pending = None
        if form_id:
            pending = self.forms.thread(f"{thread_id}-{form_id}"[:100]).get("pending_card")
        return {"thread_id": thread_id, "messages": msgs, "pending_card": pending}

    # ------------------------------------------------------------ a turn
    async def run(self, thread_id: str, *, message: str | None = None, state: dict[str, Any] | None = None,
                  resume: dict[str, Any] | None = None, run_id: str | None = None, handoff: bool = False,
                  host: Any = None, **form_kwargs: Any) -> AsyncIterator[dict]:
        check_thread_id(thread_id)
        state = state or {}
        run_id = run_id or str(uuid.uuid4())
        mode = self.route(message, state, resume, handoff, thread_id)
        if mode == "unclear":
            mode = await self.classify(message or "", state, thread_id)
        if mode == "form":
            form = state["form"]
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
                tx.append(thread_id, new_entry("user", text=typed, form_id=fid))
            kw["capabilities"] = with_hand_back(kw.get("capabilities"))   # the form agent may give the message back
            from ..transcript import pending_card
            open_card = pending_card(tx.list(form_thread)) if resume is not None else None
            said = Said()
            back = None
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
                tx.append(thread_id, new_entry("assistant", text=said.text(), form_id=fid))
            for card in said.cards:
                tx.append(thread_id, new_entry("display", card=card, form_id=fid))
            if back is None or not typed:
                return
            async for ev in self._site_turn(thread_id, typed, state, run_id, host, form_kwargs, recorded=True):
                if ev["type"] != "RUN_STARTED":   # one run: the form's RUN_STARTED already went out
                    yield ev
            return
        async for ev in self._site_turn(thread_id, message, state, run_id, host, form_kwargs):
            yield ev

    async def _site_turn(self, thread_id: str, message: str | None, state: dict[str, Any], run_id: str,
                         host: Any, form_kwargs: dict[str, Any], recorded: bool = False) -> AsyncIterator[dict]:
        """Dushes' turn (and a same-run hand-off to a form). `recorded`: the user's message is already in
        the transcript (the form agent gave it back)."""
        tx = self.forms.transcripts
        history = [("user" if e["kind"] == "card_result" else e["kind"], e.get("text", "")) for e in tx.list(thread_id)
                   if e["kind"] in ("user", "assistant", "card_result")][-self.history:] if self.history > 0 else []
        if recorded and history and history[-1][0] == "user":
            history = history[:-1]   # the message itself goes last, not twice
        if message and not recorded:
            tx.append(thread_id, new_entry("user", text=message))
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

        has_docs = bool(self.forms.knowledge.documents_for(SCOPE))
        failed = False
        async for ev in agent.answer(self.model or self.forms.models.agent, self.site, message or "", history, page,
                                     thread_id, run_id, keep, doc_passages=self.doc_passages(message or "") if has_docs else "",
                                     ask_docs=self.ask_documents if has_docs else None, live=live,
                                     instructions=self.instructions, style=self.style, tools=self.tools, ctx=ctx,
                                     suggestions=self.suggestions, finish=False):
            if ev["type"] == "TEXT_MESSAGE_CONTENT":
                said.append(ev["delta"])
            elif ev["type"] == "RUN_ERROR":
                failed = True
            yield ev
        if said:
            tx.append(thread_id, new_entry("assistant", text="".join(said)))
        if failed:
            return
        if not handed:
            yield {"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id}
            return
        # the form agent answers now, in this same run: its words and cards follow Dushes' open_form
        fid, form = handed["form_id"], handed["form"]
        form_thread = f"{thread_id}-{fid}"[:100]
        out = Said()
        async for ev in self.forms.run(form_thread, message=handoff_message(handed["note"], handed["language"]),
                                       state=form, run_id=run_id, **form_kwargs):
            if ev["type"] == "RUN_STARTED":
                continue
            out.see(ev)
            yield ev
        if out.text().strip():
            tx.append(thread_id, new_entry("assistant", text=out.text(), form_id=fid))
        for card in out.cards:
            tx.append(thread_id, new_entry("display", card=card, form_id=fid))


def create_dushes_router(site: Dushes, host: Any = None):
    """FastAPI router: POST /run (AG-UI RunAgentInput; state {page, form?}), GET /map (the site map for the page).
    `host(request)` (sync or async) builds the host's object for each run: SiteRunCtx.host in every callback."""
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

    @r.post("/transcribe")
    async def transcribe(file: UploadFile = File(...), language: str | None = Form(None)) -> dict:
        """Dictation for the site chat: the form guide's transcription."""
        from ..server import transcribe_upload
        return await transcribe_upload(site.forms, file, language)

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
        enc = agui.encoder(request.headers.get("accept"))

        async def events():
            async for ev in site.run(**kw):
                yield agui.encode(ev, enc)

        return StreamingResponse(events(), media_type=enc.get_content_type(),
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return r


# the names before Dushes, kept so existing hosts keep working
SiteGuide = Dushes
create_site_router = create_dushes_router
