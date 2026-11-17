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


def chooser_for(settings: Settings) -> Chooser | None:
    """The chooser a provider setting stands for. The one place a supplier's client is named.
    "jev" and "haiku" have no client yet (the QA Lead's measurement and the owner's yes come first): they give no
    chooser, so the layer behaves as off. "rules" is for tests."""
    if settings.provider == "rules":
        if not settings.testing:
            raise ValueError("the rules chooser is for tests only: set testing=True")
        return RulesChooser()
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
