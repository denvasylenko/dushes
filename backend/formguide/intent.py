"""The choice layer in front of the agents (internal; the CTO's D-29, openspec/changes/intent-layer).

A typed or spoken phrase is first put to a chooser as a choice among options this module generates from the form
and the screen map. A confident pick made in time can be carried out without an agent turn; anything else (no
pick, low confidence, a late or failed chooser, the layer switched off) goes to the agent as it always did.

This file is the frame only: the contract, the generated questions, the settings and the fallback. It is not wired
into a run yet, and no supplier's client is here. The layer is off unless a host of ours turns it on.

    layer = Layer(Settings(provider="off"))            # the default: every phrase goes to the agent
    pick = await layer.pick("open requests", "en", screen_question(site_map), screen="/today")
    if pick is None: ...                               # the agent takes the turn

Rules for whoever adds a chooser: implement `Chooser`, register it in `chooser_for`, and keep the supplier's name
out of every other file. A chooser outside this process gets the phrase and the option labels and nothing else.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

from . import voice as _voice

MAX_OPTIONS = 255
# what a pick may be carried out as; "understand" picks decide where the phrase goes and carry out nothing
ACTS = ("navigate", "show", "set_field")
PROVIDERS = ("jev", "haiku", "rules", "off")
# never sent to a chooser, whatever a host adds: a phone number or an e-mail in the phrase or in a label
_PRIVATE = re.compile(r"(\+?\d[\d\s().-]{6,}\d)|([\w.+-]+@[\w-]+\.[\w.-]+)")


# The CPO's two rules for the layer, in code, no model involved (2026-11-17, after the QA Lead's five sets):
# 1. a date is never a navigation: a line with a date or a weekday is not put to the chooser as a place to go;
# 2. a person's name that is not on the screen always goes to the agent (and is never sent out).
_DATE = re.compile(
    r"(?<!\w)(monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|tomorrow|tonight|yesterday|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|heute|morgen|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|demain|aujourd'hui|luned\u00ec|marted\u00ec|mercoled\u00ec|gioved\u00ec|venerd\u00ec|sabato|domenica|oggi|domani|lunes|martes|mi\u00e9rcoles|jueves|viernes|s\u00e1bado|domingo|hoy|ma\u00f1ana|\u043f\u043e\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u0438\u043a|\u0432\u0442\u043e\u0440\u043d\u0438\u043a|\u0441\u0440\u0435\u0434[\u0430\u0443\u0435]|\u0447\u0435\u0442\u0432\u0435\u0440\u0433|\u043f\u044f\u0442\u043d\u0438\u0446|\u0441\u0443\u0431\u0431\u043e\u0442|\u0432\u043e\u0441\u043a\u0440\u0435\u0441\u0435\u043d\u044c|\u0441\u0435\u0433\u043e\u0434\u043d\u044f|\u0437\u0430\u0432\u0442\u0440\u0430|\u043f\u043e\u0441\u043b\u0435\u0437\u0430\u0432\u0442\u0440\u0430|\u0432\u0447\u0435\u0440\u0430|\u043f\u043e\u043d\u0435\u0434\u0456\u043b|\u0432\u0456\u0432\u0442\u043e\u0440|\u0441\u0435\u0440\u0435\u0434[\u0430\u0443\u0438]|\u0447\u0435\u0442\u0432\u0435\u0440|\u043f'\u044f\u0442\u043d\u0438\u0446|\u0441\u0443\u0431\u043e\u0442|\u043d\u0435\u0434\u0456\u043b|\u0441\u044c\u043e\u0433\u043e\u0434\u043d\u0456|\u043f\u0456\u0441\u043b\u044f\u0437\u0430\u0432\u0442\u0440\u0430|\u0432\u0447\u043e\u0440\u0430)"
    r"|\b\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?\b|\b\d{1,2}(st|nd|rd|th)\b",
    re.IGNORECASE)
_CAPITAL = re.compile("[A-Z" + chr(0xC0) + "-" + chr(0xDE) + chr(0x400) + "-" + chr(0x42F) + r"][\w'-]+")


_EDGES = chr(34) + chr(39) + "(,.!?:;"   # what may stand around a word


def has_date(phrase: str) -> bool:
    return bool(_DATE.search(phrase or ""))


def names_off_screen(phrase: str, on_screen: Any) -> bool:
    """Whether the line holds a capitalised word, after its first word, that no label on the screen has: most
    likely a person or a company the chooser was never shown. `on_screen`: the labels the screen shows."""
    known = {w.lower() for label in on_screen for w in re.findall(r"[\w'-]+", str(label))}
    words = (phrase or "").split()
    for word in words[1:]:
        m = _CAPITAL.match(word.strip(_EDGES))
        if m and len(m.group(0)) > 1 and m.group(0).lower().rstrip("'s") not in known and m.group(0).lower() not in known:
            return True
    return False


@dataclass(frozen=True)
class Option:
    id: str
    label: str            # what the person would say; never a guest's name or phone


@dataclass(frozen=True)
class Question:
    kind: str             # "choice" | "noul" (a yes / no question: the answer is "yes" or "no" with its probability)
    about: str            # what is decided: "turn", "confirm", "language", "screen", "element", "field:<name>", ...
    text: str             # the question in plain words, for a chooser that reads one
    options: tuple[Option, ...] = ()
    act: str = "understand"   # what carrying the pick out would be: one of ACTS, or "understand"


@dataclass(frozen=True)
class Pick:
    id: str | None        # an option's id, "yes" / "no" for a noul, or None
    confidence: float     # 0..1
    ms: int = 0
    by: str = ""          # the kind of implementation ("rules", "external"), never a supplier's name


class Chooser(Protocol):
    by: str

    async def choose(self, phrase: str, language: str, question: Question, screen: str) -> Pick: ...


@dataclass(frozen=True)
class Settings:
    """Internal settings of the layer; not public configuration keys. The default changes nothing for a host."""
    provider: str = "off"                       # one of PROVIDERS
    threshold: float = 0.9                      # a placeholder until the QA Lead's measurement sets it
    timeout_ms: int = 300                       # the deadline for one pick; late is no pick
    acts: tuple[str, ...] = ACTS                # the kinds the layer may carry out by itself
    never_send: tuple[str, ...] = ()            # a host's own list: its guests' names and phones
    testing: bool = False                       # "rules" is for tests only (13% confident errors on new phrasings)

    @classmethod
    def from_env(cls) -> "Settings":
        import os
        return cls(provider=os.environ.get("INTENT_PROVIDER", "off"),
                   threshold=float(os.environ.get("INTENT_THRESHOLD", "0.8")),
                   timeout_ms=int(os.environ.get("INTENT_TIMEOUT_MS", "300")),
                   never_send=tuple(x for x in os.environ.get("INTENT_NEVER_SEND", "").split("|") if x))

    def __post_init__(self) -> None:
        if self.provider not in PROVIDERS:
            raise ValueError(f"unknown provider {self.provider!r}: one of {', '.join(PROVIDERS)}")
        if any(a not in ACTS for a in self.acts):
            raise ValueError(f"the layer acts only as {', '.join(ACTS)}: looking and reversible edits")


# ---------------------------------------------------------------- the questions, generated

def turn_question() -> Question:
    """Group 1: what kind of turn this is. "question" and "free_text" go straight to the agent."""
    return Question("choice", "turn", "What does the person want to do?", (
        Option("navigate", "go to another screen"), Option("open", "open or show something on this screen"),
        Option("pick", "choose a value from options"), Option("edit", "change a value"),
        Option("question", "ask a question"), Option("free_text", "say something that is not a choice")))


def command_question() -> Question:
    return Question("noul", "command", "Is this a command to do something?")


def confirm_question() -> Question:
    """Group 1: an answer to a confirmation that is waiting."""
    return Question("choice", "confirm", "Is this an answer to the confirmation?", (
        Option("yes", "yes"), Option("no", "no"), Option("none", "not an answer to it")))


def language_question(languages: dict[str, str]) -> Question:
    """`languages`: code -> the language's name, six at most in the first step."""
    return Question("choice", "language", "Which language is the person using?",
                    tuple(Option(code, name) for code, name in list(languages.items())[:MAX_OPTIONS]))


def screen_question(site: Any) -> Question:
    """Group 2: which screen. `site` is a SiteMap (its pages' titles are what a person says)."""
    return Question("choice", "screen", "Which screen does the person want?",
                    tuple(Option(p.path, p.title) for p in list(site.pages)[:MAX_OPTIONS]), act="navigate")


def element_question(page: Any) -> Question:
    """Group 2: which element of the current screen (a tab, an accordion, a section)."""
    return Question("choice", "element", "Which part of this screen does the person mean?",
                    tuple(Option(x.id, x.title) for x in list(page.parts)[:MAX_OPTIONS]), act="show")


def record_question(records: list[dict[str, Any]], what: str = "request") -> Question:
    """Group 2: a request or a booking, by its number or its time. A name is never an option: `records` are
    {id, number?, time?}, and anything else in them is ignored."""
    opts = []
    for r in records[:MAX_OPTIONS]:
        label = " ".join(str(r[k]) for k in ("number", "time") if r.get(k) not in (None, ""))
        if r.get("id") is not None and label:
            opts.append(Option(str(r["id"]), label))
    return Question("choice", what, f"Which {what} does the person mean?", tuple(opts), act="show")


_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_WHEN = (("today", "today"), ("tomorrow", "tomorrow"), ("day_after", "the day after tomorrow"))


def field_question(name: str, label: str, role: str, options: list[dict] | None = None,
                   low: int | None = None, high: int | None = None) -> Question | None:
    """Group 3: the question for one field, or None when the field is not a choice (free text, a file, a large
    number). `role` is the layout's: select, radio, bool, date, number, multiselect."""
    about, text = f"field:{name}", f'Which value for "{label or name}"?'
    if role in ("select", "radio", "multiselect") and options:
        opts = tuple(Option(str(o.get("id")), str(o.get("name") or o.get("id"))) for o in options[:MAX_OPTIONS]
                     if o.get("id") is not None)
        return Question("choice", about, text, opts, act="set_field") if opts else None
    if role == "bool":
        return Question("noul", about, f'Should "{label or name}" be on?', act="set_field")
    if role == "date":
        return Question("choice", about, text, tuple(Option(i, t) for i, t in _WHEN) + tuple(Option(d, d) for d in _DAYS),
                        act="set_field")
    if role == "number" and low is not None and high is not None and 0 < high - low < MAX_OPTIONS:
        return Question("choice", about, text, tuple(Option(str(n), str(n)) for n in range(low, high + 1)), act="set_field")
    return None


def form_questions(overlay: Any) -> list[Question]:
    """The questions of a form as it is now: one per field the person can edit that is a choice. `overlay` is a
    form Overlay; a hidden, disabled or read-only field has no question, and neither has free text."""
    out = []
    for node in overlay.layout.fields():
        e = overlay.get(node.name)
        if e is None or not e.editable:
            continue
        q = field_question(node.name, e.label or node.name, node.role, e.options,
                           e.props.get("min"), e.props.get("max"))
        if q:
            out.append(q)
    return out


def field_for_text_question(overlay: Any) -> Question | None:
    """Group 4: which field a piece of free text is for (the agent then fills it)."""
    opts = []
    for node in overlay.layout.fields():
        e = overlay.get(node.name)
        if e is not None and e.editable and node.role == "text":
            opts.append(Option(node.name, e.label or node.name))
    return Question("choice", "text_field", "Which field is this text for?", tuple(opts[:MAX_OPTIONS])) if opts else None


# ---------------------------------------------------------------- the layer: the deadline, the threshold, what leaves

class Layer:
    """Asks a chooser and decides whether its answer may be used. `pick` returns a Pick only when every condition
    holds; None always means "the agent takes the turn"."""

    def __init__(self, settings: Settings | None = None, chooser: Chooser | None = None):
        self.settings = settings or Settings()
        self.chooser = chooser if chooser is not None else chooser_for(self.settings)

    @property
    def on(self) -> bool:
        return self.settings.provider != "off" and self.chooser is not None

    def private(self, text: str) -> bool:
        """Whether a text holds what never leaves the process: a phone, an e-mail, or an item of `never_send`."""
        low = (text or "").lower()
        return bool(_PRIVATE.search(text or "")) or any(x and x.lower() in low for x in self.settings.never_send)

    def cleaned(self, question: Question) -> Question:
        """The question with every option whose label is private left out."""
        keep = tuple(o for o in question.options[:MAX_OPTIONS] if not self.private(o.label))
        return question if keep == question.options else Question(question.kind, question.about, question.text, keep,
                                                                  question.act)

    async def pick(self, phrase: str, language: str, question: Question, screen: str = "") -> Pick | None:
        s = self.settings
        if not self.on or not (phrase or "").strip():
            return None
        if question.act != "understand" and question.act not in s.acts:
            return None                         # not a kind the layer carries out by itself
        if self.private(phrase):
            return None                         # a guest's name or a phone in the phrase: it stays here
        q = self.cleaned(question)
        if q.kind == "choice" and not q.options:
            return None
        started = time.monotonic()
        try:
            got = await asyncio.wait_for(self.chooser.choose(phrase, language, q, screen), s.timeout_ms / 1000)
        except Exception:  # noqa: BLE001 - late, failed or unreachable: the agent takes the turn
            return None
        if not isinstance(got, Pick) or got.id is None or got.confidence < s.threshold:
            return None
        allowed = {"yes", "no"} if q.kind == "noul" else {o.id for o in q.options}
        if got.id not in allowed:
            return None                         # an id the chooser made up
        return Pick(got.id, got.confidence, round((time.monotonic() - started) * 1000), self.chooser.by)


async def _many(layer: "Layer", phrase: str, language: str, questions: dict[str, Question],
                screen: str = "") -> dict[str, Pick]:
    """Every question about one phrase in one call, under one deadline. The result holds only the picks that may
    be used (in time, confident, an id among the options sent); a missing name means "no pick". A chooser without
    `choose_many` is asked one question at a time."""
    s = layer.settings
    if not layer.on or not (phrase or "").strip() or layer.private(phrase):
        return {}
    asked = {name: layer.cleaned(q) for name, q in questions.items()
             if q.act == "understand" or q.act in s.acts}
    asked = {name: q for name, q in asked.items() if q.kind == "noul" or q.options}
    if not asked:
        return {}
    started = time.monotonic()
    try:
        if hasattr(layer.chooser, "choose_many"):
            got = await asyncio.wait_for(layer.chooser.choose_many(phrase, language, asked, screen), s.timeout_ms / 1000)
        else:
            got = {}
            for name, q in asked.items():
                left = s.timeout_ms / 1000 - (time.monotonic() - started)
                got[name] = await asyncio.wait_for(layer.chooser.choose(phrase, language, q, screen), max(left, 0.001))
    except Exception:  # noqa: BLE001 - late, failed or unreachable: the agent takes the turn
        return {}
    ms, out = round((time.monotonic() - started) * 1000), {}
    for name, q in asked.items():
        p = got.get(name)
        allowed = {"yes", "no"} if q.kind == "noul" else {o.id for o in q.options}
        if isinstance(p, Pick) and p.id in allowed and p.confidence >= s.threshold:
            out[name] = Pick(p.id, p.confidence, ms, layer.chooser.by)
    return out


Layer.pick_many = _many   # type: ignore[attr-defined]


def value_question(overlay: Any, consents: Any = ()) -> Question | None:
    """Group 3 in one question: every value of every choice field the person can edit, as "field: option". A
    checkbox is "field: yes". A consent is never an option: only the person gives it."""
    opts: list[Option] = []
    for node in overlay.layout.fields():
        e = overlay.get(node.name)
        if e is None or not e.editable or node.name in consents:
            continue
        label = e.label or node.name
        if node.role in ("select", "radio") and e.options:
            opts += [Option(f"{node.name}={o.get('id')}", f"{label}: {o.get('name') or o.get('id')}")
                     for o in e.options if o.get("id") is not None]
        elif node.role == "bool":
            opts.append(Option(f"{node.name}=true", f"{label}: yes"))
    return Question("choice", "value", "Which value does the line name outright, as it is written on the screen?",
                    tuple(opts[:MAX_OPTIONS - 1]), act="set_field") if opts else None


# ---------------------------------------------------------------- a picked value goes through the form's own card

_PRESETS: dict[str, dict] = {}   # the form thread -> {"script": what the form agent's model would have said, "needs": ...}
APPLIED = "The user confirmed; changes applied"   # how the form agent's tool result starts when a card was applied


def preset_call(thread_id: str, tool: str, args: dict, closing: str, needs: str = "") -> None:
    """The layer decided the form agent's next two steps on this thread: call this tool, then say this line. So
    the form's own tool, checks and Undo apply and no model is called. `needs`: how the tool's result must start
    for the closing line to be said."""
    from langchain_core.messages import AIMessage
    _PRESETS[thread_id] = {"needs": needs, "script": [
        AIMessage(content="", tool_calls=[{"name": tool, "id": f"fast_{int(time.time() * 1000)}", "args": args}]),
        AIMessage(content=closing)]}


def preset(thread_id: str, name: str, value: Any, label: str, shown: str) -> None:
    """A value the layer picked for a field: proposed on the form's own card, then said in one line."""
    preset_call(thread_id, "propose_changes", {"changes": [{"name": name, "value": value}]}, f"{label}: {shown}.", APPLIED)


def clear_preset(thread_id: str) -> None:
    _PRESETS.pop(thread_id, None)


def has_preset(thread_id: str) -> bool:
    return bool((_PRESETS.get(thread_id) or {}).get("script"))


def is_fill(thread_id: str) -> bool:
    """Whether what is decided for this thread is a value for a field (its card is applied at once)."""
    return has_preset(thread_id) and _PRESETS[thread_id]["needs"] == APPLIED


def preset_model(thread_id: str | None, messages: list | None = None) -> Any:
    """A model that says the decided steps, or None when nothing is decided for this thread. The closing line
    ("Loan type: Car loan.") is said only when the tool did what was decided with no complaint: a value the form
    or the server refused, a card the person rejected, an error after the change are handed back to the agent,
    which explains and offers what is possible. The layer never says a thing is done that is not."""
    entry = _PRESETS.get(thread_id or "")
    script = (entry or {}).get("script")
    if not script:
        return None
    if len(script) == 1 and messages is not None:
        last = messages[-1] if messages else None
        said = str(getattr(last, "content", "") or "")
        fine = (type(last).__name__ == "ToolMessage" and getattr(last, "status", "success") != "error"
                and said.startswith(entry["needs"]) and not any(x in said.lower() for x in ("error", "not accepted", "\u26a0")))
        if not fine:
            _PRESETS.pop(thread_id or "", None)
            return None
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessageChunk
    from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

    class Decided(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "decided"

        def bind_tools(self, tools, **kwargs):  # type: ignore[override]
            return self

        def _next(self):
            msg = script.pop(0)
            if not script:
                _PRESETS.pop(thread_id or "", None)
            return msg

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=self._next())])

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            import json
            msg = self._next()
            if msg.content:
                yield ChatGenerationChunk(message=AIMessageChunk(content=msg.content))
            for i, tc in enumerate(msg.tool_calls):
                yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[
                    {"name": tc["name"], "args": json.dumps(tc["args"], ensure_ascii=False), "id": tc["id"], "index": i}]))

    return Decided()


def parts_question(site: Any) -> Question:
    """Group 2: a part of any page (a tab, an accordion, a section), as "page: part". Its id is "path#part"."""
    opts = [Option(f"{p.path}#{x.id}", f"{p.title}: {x.title}") for p in site.pages for x in p.parts]
    return Question("choice", "element", "Which part of a page does the line name?", tuple(opts[:MAX_OPTIONS - 1]), act="show")


def form_part_question(overlay: Any) -> Question | None:
    """Group 2: a tab, an accordion or a section of the form on this screen (the person sees them by their labels)."""
    opts = []
    for node in overlay.layout.nodes.values():
        if node.role in ("tab", "accordion", "section") and node.name:
            e = overlay.get(node.name)
            label = (e.label if e is not None else None) or node.text
            if label and (e is None or e.visible):
                opts.append(Option(node.name, str(label)))
    return Question("choice", "form_part", "Which part of the form on this screen does the line name?",
                    tuple(opts[:MAX_OPTIONS - 1]), act="show") if opts else None


def chooser_for(settings: Settings) -> Chooser | None:
    """The chooser a provider setting stands for. The one place a supplier's client is named.
    "jev" and "haiku" have no client yet (the QA Lead's measurement and the owner's yes come first): they give no
    chooser, so the layer behaves as off. "rules" is for tests."""
    if settings.provider == "rules":
        if not settings.testing:
            raise ValueError("the rules chooser is for tests only: set testing=True")
        return RulesChooser()
    if settings.provider == "jev":   # demo branch: the client exists here; without a key the layer is off
        from .intent_external import from_env
        return from_env()
    return None


class RulesChooser:
    """For tests: an option whose label is in the phrase word for word, or a plain yes / no. Not for a product:
    on new phrasings it was confidently wrong 13% of the time (the QA Lead's measurement, 2026-11-17)."""
    by = "rules"

    async def choose(self, phrase: str, language: str, question: Question, screen: str) -> Pick:
        text = " " + " ".join(re.findall(r"\w+", (phrase or "").lower())) + " "
        if question.kind == "noul":
            said = _voice.yes_or_no(phrase)
            return Pick(None if said is None else ("yes" if said else "no"), 0.0 if said is None else 1.0)
        hits = [o for o in question.options
                if (label := " ".join(re.findall(r"\w+", o.label.lower()))) and f" {label} " in text]
        return Pick(hits[0].id, 1.0) if len(hits) == 1 else Pick(None, 0.0)
