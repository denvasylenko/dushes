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


def said_in(label: str, phrase: str) -> bool:
    """Whether a part's own name is said in the line: every word of it (of three letters or more), by its first
    five letters. A chooser asked "which part?" names the nearest one even when the line names none of them; a
    part is opened only when the person said it."""
    words = [w for w in re.findall(r"[\w']+", (label or "").lower()) if len(w) >= 3]
    heard = {w[:5] for w in re.findall(r"[\w']+", (phrase or "").lower())}
    return bool(words) and all(w[:5] in heard for w in words)


_ORDER_WORDS = set("""open show go goto take bring get navigate switch move jump see view display me us my the a an to
    into in on at of for from and or page pages screen section tab part please can could would will you now okay ok
    yeah yes hey so then just again want need like let lets i id we""".split())


_TAKES = set("it this that one them there here yes yeah yep sure ok okay first second third please do".split())


def takes_up(phrase: str) -> bool:
    """Whether the line only takes up what was just offered ("open it", "yes please", "can you open it?", "that
    one"): nothing in it but the order, a yes and a pointing word. Anything more ("yes, but what does it cost?")
    is a new line for the model."""
    words = re.findall(r"[\w']+", (phrase or "").lower())
    return bool(words) and len(words) <= 6 and all(w in _ORDER_WORDS or w in _TAKES for w in words)


def names_more(phrase: str, place: str) -> bool:
    """Whether a line that orders a move says more than the place: a word of four letters or more that is neither
    a word of the place's name nor a word of the order itself. "Open personal details in loan application" names
    more than the page "Apply for a loan"; "can you open car insurance" does not name more than "Car insurance".
    Decided in code: asked whether a part is named, a chooser said no to that very line."""
    known = {w[:4] for w in re.findall(r"[\w']+", (place or "").lower())}
    for w in re.findall(r"[\w']+", (phrase or "").lower()):
        if len(w) >= 4 and w not in _ORDER_WORDS and w[:4] not in known:
            return True
    return False


def mask_names(phrase: str, on_screen: Any) -> tuple[str, bool]:
    """The line as it may go to a chooser: a capitalised word, after the first, that no label of the screen has
    (most likely a person or a company) is replaced by "<name>". Returns the line and whether anything was."""
    known = {w.lower() for label in on_screen for w in re.findall(r"[\w'-]+", str(label))} | set(_MONTHS) | set(_DAYS)
    words, found = (phrase or "").split(), False
    for i, word in enumerate(words[1:], 1):
        if word.strip(_EDGES).lower() in _STARTERS:
            continue                                  # an everyday word, capital because it opens a sentence or a clause
                                                      # ("Oh Okay, okay. Open ..."): nobody's name wherever it stands
        m = _CAPITAL.match(word.strip(_EDGES))
        if m and len(m.group(0)) > 1 and m.group(0).lower().rstrip("'s") not in known and m.group(0).lower() not in known:
            words[i] = word.replace(m.group(0), "<name>")
            found = True
    return " ".join(words), found


def has_date(phrase: str) -> bool:
    return bool(_DATE.search(phrase or ""))


# everyday words a sentence opens with: capital there, and nobody's name (anything else capital may be one)
_STARTERS = set("""so then and but or okay ok yes yeah no well also now please can could would will what which how where
    when why who whom i i'm i'd i'll my me we our the a an it it's is are do does did set open show go put add make
    let let's that this these those there here if just thanks thank hello hi hey uh um oh""".split())


def names_off_screen(phrase: str, on_screen: Any) -> bool:
    """Whether the line holds a capitalised word, after its first word, that no label on the screen has: most
    likely a person or a company the chooser was never shown. `on_screen`: the labels the screen shows."""
    known = {w.lower() for label in on_screen for w in re.findall(r"[\w'-]+", str(label))}
    known |= set(_MONTHS) | set(_DAYS)          # "1st July 2014", "on Friday": a month or a weekday is nobody's name
    words = (phrase or "").split()
    for i, word in enumerate(words[1:], 1):
        if word.strip(_EDGES).lower() in _STARTERS:
            continue                                  # an everyday word, capital because it opens a sentence or a clause
                                                      # ("Oh Okay, okay. Open ..."): nobody's name wherever it stands
        m = _CAPITAL.match(word.strip(_EDGES))
        if m and len(m.group(0)) > 1 and m.group(0).lower().rstrip("'s") not in known and m.group(0).lower() not in known:
            return True
    return False


@dataclass(frozen=True)
class Option:
    id: str
    label: str            # what the person would say; never a guest's name or phone
    hint: str = ""        # what is there, in the host's own words (a page's description, its keywords): only a
    #                       chooser reads it, beside the label; never shown or said


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
    act: float = 0.8                            # the tool acts at or above it (a placeholder until the measurement)
    margin: float = 0.2                         # ... and only when the first option is this clear of the second

    @classmethod
    def from_env(cls) -> "Settings":
        import os
        return cls(provider=os.environ.get("INTENT_PROVIDER", "off"),
                   threshold=float(os.environ.get("INTENT_THRESHOLD", "0.8")),
                   timeout_ms=int(os.environ.get("INTENT_TIMEOUT_MS", "300")),
                   never_send=tuple(x for x in os.environ.get("INTENT_NEVER_SEND", "").split("|") if x),
                   act=float(os.environ.get("INTENT_ACT", "0.8")), margin=float(os.environ.get("INTENT_MARGIN", "0.2")))

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

    def also_never(self, items: tuple[str, ...]) -> "Layer":
        """This layer with more never-send items, for one run (a site's own guests' names): the same chooser and
        settings otherwise."""
        import copy
        import dataclasses
        other = copy.copy(self)
        other.settings = dataclasses.replace(self.settings, never_send=(*self.settings.never_send, *items))
        return other

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


_PRIVATE_BITS = re.compile(r"([\w.+-]+@[\w-]+\.[\w.-]+)|((?<![\w/.])\+?(?:\d[ \t().-]{0,2}){6,}\d(?![\w/]))")


def scrub(layer: "Layer", text: str, limit: int = 0) -> str:
    """A text as it may leave the process: every e-mail, phone and long run of digits, and every item of the
    host's never-send list, replaced by "<filled>"; cut to `limit` characters when one is given."""
    out = _PRIVATE_BITS.sub("<filled>", str(text or ""))
    for item in layer.settings.never_send:
        if item:
            out = re.sub(re.escape(item), "<filled>", out, flags=re.IGNORECASE)
    return out[:limit] if limit else out


def safe_context(layer: "Layer", context: dict[str, Any] | None) -> dict[str, Any]:
    """What a chooser is told beside the line, with the owner's filter over every piece (the assistant's own words
    included): nothing private goes out as a value, it goes as "<filled>". Empty pieces are left out."""
    out: dict[str, Any] = {}
    for key, value in (context or {}).items():
        if isinstance(value, list):
            kept = [scrub(layer, v, 300) for v in value if v not in (None, "")]
            if kept:
                out[key] = kept
        elif value not in (None, ""):
            out[key] = scrub(layer, value, 6000)
    return out


async def _many(layer: "Layer", phrase: str, language: str, questions: dict[str, Question],
                screen: str = "", context: dict[str, Any] | None = None, trace: list | None = None) -> dict[str, Pick]:
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
            ctx = safe_context(layer, context)
            call = (layer.chooser.choose_many(phrase, language, asked, screen, ctx) if ctx
                    else layer.chooser.choose_many(phrase, language, asked, screen))
            got = await asyncio.wait_for(call, s.timeout_ms / 1000)
        else:
            got = {}
            for name, q in asked.items():
                left = s.timeout_ms / 1000 - (time.monotonic() - started)
                got[name] = await asyncio.wait_for(layer.chooser.choose(phrase, language, q, screen), max(left, 0.001))
    except Exception:  # noqa: BLE001 - late, failed or unreachable: the agent takes the turn
        return {}
    ms, out = round((time.monotonic() - started) * 1000), {}
    probs = getattr(layer.chooser, "probs", {}) or {}
    for name, q in asked.items():
        p = got.get(name)
        allowed = {"yes", "no"} if q.kind == "noul" else {o.id for o in q.options}
        used = isinstance(p, Pick) and p.id in allowed and p.confidence >= s.threshold
        if used:
            out[name] = Pick(p.id, p.confidence, ms, layer.chooser.by)
        if trace is not None:   # every question and its answer, used or not, for a host that shows how a turn was decided
            labels = {o.id: o.label for o in q.options}
            top = sorted(((i, v) for i, v in (probs.get(name) or {}).items() if i in labels), key=lambda t: -t[1])[:3]
            trace.append({"about": q.about, "text": q.text, "kind": q.kind,
                          "answer": p.id if isinstance(p, Pick) else None,
                          "answer_label": labels.get(p.id) if isinstance(p, Pick) and p.id else (p.id if isinstance(p, Pick) else None),
                          "p": round(p.confidence, 3) if isinstance(p, Pick) else None, "used": bool(used),
                          **({"options": [{"id": i, "label": labels[i], "p": round(v, 3)} for i, v in top]} if q.kind == "choice" and top else {})})
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


def field_questions(overlay: Any, names: list[str], consents: Any = ()) -> dict[str, Question]:
    """One question a field, for the choice fields and checkboxes among `names` (the fields on the screen), so a
    line that names several values gets an answer for each: "f:<field>" -> its options as "field: option" (a
    checkbox is "field: yes"). A consent is never asked about."""
    out: dict[str, Question] = {}
    for name in names:
        e = overlay.get(name)
        if e is None or not e.editable or name in consents:
            continue
        label = e.label or name
        if e.node.role in ("select", "radio") and e.options:
            opts = tuple(Option(f"{name}={o.get('id')}", f"{label}: {o.get('name') or o.get('id')}")
                         for o in e.options if o.get("id") is not None)[:MAX_OPTIONS - 1]
        elif e.node.role == "bool":
            opts = (Option(f"{name}=true", f"{label}: yes"), Option(f"{name}=false", f"{label}: no"))
        else:
            continue
        out[f"f:{name}"] = Question("choice", f"field:{name}", f'Does the line give a value for "{label}"? Which one?',
                                    opts, act="set_field")
    return out


def says_any(label: str, phrase: str) -> bool:
    """Whether the line says at least one word of the label (four letters or more, by its first five)."""
    heard = {w[:5] for w in re.findall(r"[\w']+", (phrase or "").lower())}
    return any(w[:5] in heard for w in re.findall(r"[\w']+", (label or "").lower()) if len(w) >= 4)


# ---------------------------------------------------------------- a picked value goes through the form's own card

_PRESETS: dict[str, dict] = {}   # the form thread -> {"script": what the UI agent's model would have said, "needs": ...}
APPLIED = "The user confirmed; changes applied"   # how the UI agent's tool result starts when a card was applied


def preset_calls(thread_id: str, calls: list[tuple[str, dict]], closing: str, needs: str = "") -> None:
    """As preset_call, with several calls of the UI agent's tools in one step (several sections to open)."""
    from langchain_core.messages import AIMessage
    stamp = int(time.time() * 1000)
    _PRESETS[thread_id] = {"needs": needs, "tail": not closing, "script": [
        AIMessage(content="", tool_calls=[{"name": tool, "id": f"fast_{stamp}_{i}", "args": args}
                                          for i, (tool, args) in enumerate(calls)]),
        *([AIMessage(content=closing)] if closing else [])]}


def preset_call(thread_id: str, tool: str, args: dict, closing: str, needs: str = "") -> None:
    """The layer decided the UI agent's next two steps on this thread: call this tool, then say this line. So
    the form's own tool, checks and Undo apply and no model is called. `needs`: how the tool's result must start
    for the closing line to be said."""
    from langchain_core.messages import AIMessage
    # no closing line: the line holds more than the layer did, so after the tool the form's own model goes on (it
    # sees the call and its result in the conversation, so it knows what is done already)
    _PRESETS[thread_id] = {"needs": needs, "tail": not closing, "script": [
        AIMessage(content="", tool_calls=[{"name": tool, "id": f"fast_{int(time.time() * 1000)}", "args": args}]),
        *([AIMessage(content=closing)] if closing else [])]}


def preset(thread_id: str, name: str, value: Any, label: str, shown: str) -> None:
    """A value the layer picked for a field: proposed on the form's own card, then said in one line."""
    preset_call(thread_id, "propose_changes", {"changes": [{"name": name, "value": value}]}, f"{label}: {shown}.", APPLIED)


def preset_closing(thread_id: str, closing: str, fields: list[str]) -> None:
    """After a card of the form's UI agent that is applied at once (every value said outright): when the form
    takes it with no complaint, the turn ends with this one line written in code, and the model is not called a
    second time only to say it (the owner's standard: done, one short line). `fields`: the card's fields, so the
    line is said only after that very card."""
    from langchain_core.messages import AIMessage
    if not has_preset(thread_id):
        _PRESETS[thread_id] = {"needs": APPLIED, "fields": list(fields), "at": time.time(), "script": [AIMessage(content=closing)]}


def clean_result(said: str) -> bool:
    """Whether the form took an applied card with nothing to explain: nothing refused, edited or declined, no new
    error, and nothing appeared, hid or became required. An error that went away is not a complaint."""
    low = (said or "").lower().replace("error fixed", "")
    return not any(x in low for x in ("error", "not accepted", "\u26a0", "hidden", "disabled", "locked", "cannot", "declined",
                                      "edited before", "failed validation", "appeared", "became required"))


def clear_preset(thread_id: str) -> None:
    _PRESETS.pop(thread_id, None)


def has_preset(thread_id: str) -> bool:
    return bool((_PRESETS.get(thread_id) or {}).get("script"))


def is_fill(thread_id: str) -> bool:
    """Whether what is decided for this thread is a value for a field (its card is applied at once). Also true
    for the card of a line with more in it: its steps are said already, the form's own model goes on after it."""
    entry = _PRESETS.get(thread_id) or {}
    return entry.get("needs") == APPLIED and bool(entry.get("script") or entry.get("tail"))


def used_fill(thread_id: str) -> None:
    """The decided card was made: when nothing else is decided, nothing is left over for the next card."""
    entry = _PRESETS.get(thread_id)
    if entry is not None and not entry.get("script"):
        _PRESETS.pop(thread_id, None)


def preset_model(thread_id: str | None, messages: list | None = None) -> Any:
    """A model that says the decided steps, or None when nothing is decided for this thread. The closing line
    ("Loan type: Car loan.") is said only when the tool did what was decided with no complaint: a value the form
    or the server refused, a card the person rejected, an error after the change are handed back to the agent,
    which explains and offers what is possible. The layer never says a thing is done that is not."""
    entry = _PRESETS.get(thread_id or "")
    script = (entry or {}).get("script")
    if not script:
        return None
    if len(script) == 1 and script[0].content and messages is not None:
        last = messages[-1] if messages else None
        said = str(getattr(last, "content", "") or "")
        fine = (type(last).__name__ == "ToolMessage" and getattr(last, "status", "success") != "error"
                and said.startswith(entry["needs"]) and clean_result(said)
                and all(f in said for f in entry.get("fields") or [])                 # this very card's answer
                and time.time() - entry.get("at", time.time()) < 180)
        if not fine:
            _PRESETS.pop(thread_id or "", None)
            return None
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessageChunk
    from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

    class Decided(BaseChatModel):
        model: str = "code"   # in a run's stats: a step written in code, not a model call

        @property
        def _llm_type(self) -> str:
            return "decided"

        def bind_tools(self, tools, **kwargs):  # type: ignore[override]
            return self

        def _next(self):
            msg = script.pop(0)
            if not script and not (entry.get("tail") and entry.get("needs") == APPLIED):
                _PRESETS.pop(thread_id or "", None)   # (a card with more to answer keeps its mark until it is made)
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


# A direct command, as code sees it (the owner, 2026-11-17: "open, close, go to, scroll, plain commands"): the
# line begins, after a greeting or a polite opening, with a verb of this short list. A verb is added when a
# measured phrase needs it, never by guess.
_LEAD = r"(?:(?:ok|okay|hey|so|now|well|please|yeah|yes|and|then|just|can you|could you|would you|will you|bitte|kannst du|k\u00f6nnen sie|s'il te pla\u00eet|s'il vous pla\u00eet|peux-tu|pouvez-vous|por favor|puedes|per favore|puoi|\u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430|\u043c\u043e\u0436\u0435\u0448\u044c|\u043c\u043e\u0436\u0435\u0442\u0435|\u0430|\u043d\u0443|\u0442\u0435\u043f\u0435\u0440\u044c|\u0442\u0430\u043a|\u0431\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430|\u043c\u043e\u0436\u0435\u0448|\u043c\u043e\u0436\u0435\u0442\u0435|\u0442\u0435\u043f\u0435\u0440)[\s,.!]+)*"
_DIRECT = re.compile(r"^[\s,.!]*" + _LEAD + r"(\u043e\u0442\u043a\u0440\u044b\u0442\u044c|\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c|\u043f\u0435\u0440\u0435\u0439\u0442\u0438|\u0437\u0430\u043a\u0440\u044b\u0442\u044c|\u0432\u0456\u0434\u043a\u0440\u0438\u0442\u0438|\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u0438|aprire|mostrare|chiudere|\u00f6ffnen|zeigen|schlie\u00dfen|ouvrir|montrer|fermer|abrir|mostrar|cerrar|open|close|show|hide|go|take|bring|navigate|switch|scroll|jump|move|set|choose|select|pick|tick|untick|check|uncheck|translate|expand|collapse|\u00f6ffne|schlie\u00dfe|zeig|zeige|geh|gehe|w\u00e4hle|setze|scrolle|wechsle|ouvre|ouvrez|ferme|fermez|montre|montrez|va|allez|choisis|choisissez|mets|abre|cierra|muestra|ve|elige|selecciona|pon|apri|chiudi|mostra|vai|scegli|seleziona|metti|imposta|\u043e\u0442\u043a\u0440\u043e\u0439|\u043e\u0442\u043a\u0440\u043e\u0439\u0442\u0435|\u0437\u0430\u043a\u0440\u043e\u0439|\u0437\u0430\u043a\u0440\u043e\u0439\u0442\u0435|\u043f\u043e\u043a\u0430\u0436\u0438|\u043f\u043e\u043a\u0430\u0436\u0438\u0442\u0435|\u043f\u0435\u0440\u0435\u0439\u0434\u0438|\u043f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435|\u0432\u044b\u0431\u0435\u0440\u0438|\u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435|\u043f\u043e\u0441\u0442\u0430\u0432\u044c|\u043f\u043e\u0441\u0442\u0430\u0432\u044c\u0442\u0435|\u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438|\u043f\u0440\u043e\u043a\u0440\u0443\u0442\u0438|\u043f\u0440\u043e\u043b\u0438\u0441\u0442\u0430\u0439|\u043f\u0435\u0440\u0435\u0432\u0435\u0434\u0438|\u0432\u0456\u0434\u043a\u0440\u0438\u0439|\u0432\u0456\u0434\u043a\u0440\u0438\u0439\u0442\u0435|\u0437\u0430\u043a\u0440\u0438\u0439|\u0437\u0430\u043a\u0440\u0438\u0439\u0442\u0435|\u043f\u043e\u043a\u0430\u0436\u0438|\u043f\u043e\u043a\u0430\u0436\u0456\u0442\u044c|\u043f\u0435\u0440\u0435\u0439\u0434\u0438|\u043f\u0435\u0440\u0435\u0439\u0434\u0456\u0442\u044c|\u043e\u0431\u0435\u0440\u0438|\u043e\u0431\u0435\u0440\u0456\u0442\u044c|\u0432\u0438\u0431\u0435\u0440\u0438|\u043f\u043e\u0441\u0442\u0430\u0432|\u043f\u0435\u0440\u0435\u043c\u043a\u043d\u0438|\u043f\u0440\u043e\u043a\u0440\u0443\u0442\u0438|\u043f\u0435\u0440\u0435\u043a\u043b\u0430\u0434\u0438)(?![\w'])", re.IGNORECASE)


def is_direct(phrase: str) -> bool:
    """Whether the line begins with a verb of the short list. The other half of "direct"
    (it says no more than the place or value it names, and the chooser is sure) is decided where the options are."""
    # "open apply for loan ?" and "can you open car insurance?" are commands in a spoken or polite form: the verb
    # at the start decides, not the mark at the end (a real question starts with what, how, when...)
    return bool(_DIRECT.match((phrase or "").strip()))


# What is said around a name and is not part of it: fillers, politeness, articles, and the word for the kind of
# place. A spoken line is matched to the screen's names without them ("Okay, can you open uh the loans page").
# In the seven languages the product ships (non-ASCII letters as escapes: the repository is English-only). These are
# words of a language, never words of a site: every name comes from the host's own map.
_AROUND = set("""ok okay uh um er eh hmm so well now hey yeah yes and then just again please can could would will you help me with us my i want need like to a an the \u043d\u0443 \u0430 \u0438 \u0442\u0430\u043a \u0432\u043e\u0442 \u0442\u0435\u043f\u0435\u0440\u044c \u0435\u0449\u0435 \u0435\u0449\u0451 \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430 \u043c\u043e\u0436\u0435\u0448\u044c \u043c\u043e\u0436\u0435\u0442\u0435 \u043c\u043e\u0433\u0443 \u043c\u043d\u0435 \u043d\u0430\u043c \u043c\u043e\u0439 \u043c\u043e\u044f \u043c\u043e\u044e \u043c\u043e\u0435 \u043c\u043e\u0451 \u0445\u043e\u0447\u0443 \u043d\u0443\u0436\u043d\u043e \u043d\u0430\u0434\u043e \u0431\u044b \u0431\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430 \u043c\u043e\u0436\u0435\u0448 \u043c\u0435\u043d\u0456 \u043d\u0430\u043c \u043c\u0456\u0439 \u043c\u043e\u044f \u0445\u043e\u0447\u0443 \u0442\u0440\u0435\u0431\u0430 \u0449\u0435 \u0442\u0435\u043f\u0435\u0440 ok allora ora poi ancora per favore puoi potresti pu\u00f2 mi ci il lo la i gli le un uno una del della dei delle vorrei voglio also nun jetzt dann noch bitte kannst kann k\u00f6nntest k\u00f6nnen du sie mir mich uns der die das den dem ein eine einen ich m\u00f6chte will alors maintenant puis encore s'il te vous pla\u00eet peux pouvez tu me nous le la les un une des du je veux voudrais bueno ahora luego otra vez por favor puedes puede podr\u00edas me nos el la los las un una unos unas quiero""".split())
_KINDS = {w: kind for kind, words in {"page": "page pages screen screens \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0443 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b \u044d\u043a\u0440\u0430\u043d \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0430 \u0441\u0442\u043e\u0440\u0456\u043d\u043a\u0443 \u0435\u043a\u0440\u0430\u043d pagina schermata seite bildschirm \u00e9cran p\u00e1gina pantalla",
                                     "part": "tab tabs section sections part block accordion \u0432\u043a\u043b\u0430\u0434\u043a\u0430 \u0432\u043a\u043b\u0430\u0434\u043a\u0443 \u0440\u0430\u0437\u0434\u0435\u043b \u0441\u0435\u043a\u0446\u0438\u044f \u0441\u0435\u043a\u0446\u0438\u044e \u0431\u043b\u043e\u043a \u0432\u043a\u043b\u0430\u0434\u043a\u0430 \u0440\u043e\u0437\u0434\u0456\u043b scheda sezione reiter abschnitt bereich onglet partie pesta\u00f1a secci\u00f3n"}.items() for w in words.split()}
_GO_VERBS = set("""open show go goto take bring navigate switch scroll jump move see view display expand \u043e\u0442\u043a\u0440\u043e\u0439 \u043e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u043e\u043a\u0430\u0436\u0438 \u043f\u043e\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u043f\u0435\u0440\u0435\u0439\u0434\u0438 \u043f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043f\u0435\u0440\u0435\u0439\u0442\u0438 \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438 \u0440\u0430\u0437\u0432\u0435\u0440\u043d\u0438 \u0432\u0456\u0434\u043a\u0440\u0438\u0439 \u0432\u0456\u0434\u043a\u0440\u0438\u0439\u0442\u0435 \u0432\u0456\u0434\u043a\u0440\u0438\u0442\u0438 \u043f\u043e\u043a\u0430\u0436\u0438 \u043f\u043e\u043a\u0430\u0436\u0456\u0442\u044c \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u0438 \u043f\u0435\u0440\u0435\u0439\u0434\u0438 \u043f\u0435\u0440\u0435\u0439\u0434\u0456\u0442\u044c \u043f\u0435\u0440\u0435\u0439\u0442\u0438 apri aprire mostra mostrare vai andare porta portami \u00f6ffne \u00f6ffnen zeig zeige zeigen geh gehe gehen wechsle ouvre ouvrez ouvrir montre montrez montrer va allez aller abre abrir muestra mostrar ve ir lleva ll\u00e9vame""".split())
_REQUEST = re.compile(r"^[\W]*(?:(?:ok|okay|hey|so|now|well|yeah|yes|\u043d\u0443|\u0430|\u0442\u0430\u043a|allora|also|alors|bueno)[\s,.!]+)*("
                      r"please|can you|could you|would you|will you|\u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430|\u043c\u043e\u0436\u0435\u0448\u044c|\u043c\u043e\u0436\u0435\u0442\u0435|\u0431\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430|\u043c\u043e\u0436\u0435\u0448|per favore|puoi|potresti|bitte|kannst du|k\u00f6nnen sie|s'il te pla\u00eet|s'il vous pla\u00eet|peux-tu|pouvez-vous|por favor|puedes|podr\u00edas)(?![\w'])",
                      re.IGNORECASE)


def asks_for(phrase: str) -> bool:
    """Whether the line opens as a request ("can you ...", "please ..."), with or without a verb of the list."""
    return bool(_REQUEST.match(phrase or ""))


_ARTICLES = set("a an the il lo la i gli le un uno una der die das den dem ein eine el los las unos unas les des du".split())


def stem(word: str) -> str:
    """A word without its ending, so a case or a plural still matches: "loans" and "loan", and the forms a name
    takes in Russian, Italian or German. Short words are kept whole."""
    return word if len(word) < 5 else word[:max(4, len(word) - 2)]


def name_words(text: str) -> list[str]:
    """A name as its words, without articles, punctuation and case: "Apply for a loan" -> apply, for, loan."""
    return [stem(w) for w in re.findall(r"[\w']+", (text or "").lower()) if w not in _ARTICLES]


def match_name(phrase: str, targets: list[tuple[str, str, str]]) -> tuple[str, str, bool] | None:
    """The target a spoken or typed line names, decided in code: (id, how, more_said), or None.
    `targets`: (id, label, kind) with kind "page", "part" or "form". The line is stripped of what stands around a
    name; then, in this order: the whole name said word for word (the longest wins); then the nearest name by
    spelling, for a misheard word ("mortga-the-ges" for Mortgage), only when it is close and well clear of the
    second. A word for the kind ("page", "tab") narrows the targets to that kind. `more_said`: the line holds
    words beyond the name, so the name alone is not all that was asked."""
    import difflib
    words = [w for w in re.findall(r"[\w']+", (phrase or "").lower())]
    kinds = {_KINDS[w] for w in words if w in _KINDS}
    rest = [w for w in words if w not in _AROUND and w not in _KINDS]
    while rest and rest[0] in _GO_VERBS:
        rest = rest[1:]
    if not rest:
        return None
    heard = " ".join(rest)                       # as it was heard, for a misheard name (spelling, not stems)
    rest = [stem(w) for w in rest]               # names are compared by their stems: cases and plurals match
    spelled = {i: " ".join(w for w in re.findall(r"[\w']+", label.lower()) if w not in _ARTICLES) for i, label, _k in targets}
    pool = [(i, name_words(label), kind) for i, label, kind in targets if name_words(label)]
    if kinds:
        narrowed = [t for t in pool if ("page" if t[2] == "page" else "part") in kinds]
        pool = narrowed or pool
    said = " " + " ".join(rest) + " "
    exact = [(i, w) for i, w, _k in pool if " " + " ".join(w) + " " in said]
    if exact:
        longest = max(len(w) for _i, w in exact)
        best = [(i, w) for i, w in exact if len(w) == longest]
        if len({" ".join(w) for _i, w in best}) > 1:
            return None                          # two different names of the same length: not decided here
        i, w = best[0]
        left = [x for x in rest if x not in w and len(x) >= 4]
        return i, "said", bool(left)
    q = heard
    scored = sorted(((max(difflib.SequenceMatcher(None, q, spelled[i]).ratio(),
                          difflib.SequenceMatcher(None, q.replace(" ", ""), spelled[i].replace(" ", "")).ratio()), i)
                     for i, _w, _k in pool), reverse=True)
    if not scored:
        return None
    top, second = scored[0], (scored[1][0] if len(scored) > 1 else 0.0)
    # one bar, and a high one: a looser one for lines that say "page" or "tab" was tried and taken out again, because
    # it had been set to let one recorded line through ("we quick visit page" for Book a visit), which is fitting,
    # not measuring. These two numbers are placeholders for the QA Lead's measurement to set
    near, clear = 0.85, 0.25
    if top[0] >= near and top[0] - second >= clear:
        return top[1], "near", False
    return None


def match_path(phrase: str, targets: list[dict[str, Any]]) -> tuple[str, str] | None:
    """The object a line names, with the hierarchy taken into account: (id, how) or None.
    `targets`: {"id", "label", "kind": "page" | "part" | "form", "up": names above it (the page's title and
    keywords, the tab it sits in), "here": it is on the screen now}. The owner's line "open apply for loan,
    application, personal details" names a page, its form and a section: the section is the object, the other
    names are the way to it. A target is taken when its whole name is said and every other word of weight in the
    line belongs to a name above it. Among several, the one with the most of its way said wins; then what is on
    the screen now; then a page. Two different objects left at the top: not decided here. Failing a said name,
    a misheard one is taken as `match_name` takes it."""
    words = re.findall(r"[\w']+", (phrase or "").lower())
    rest = [w for w in words if w not in _AROUND and w not in _KINDS]
    while rest and rest[0] in _GO_VERBS:
        rest = rest[1:]
    if not rest:
        return None
    rest = [stem(w) for w in rest]               # names are compared by their stems: cases and plurals match
    said = " " + " ".join(rest) + " "

    def spans(name: list[str]) -> list[tuple[int, int]]:
        """Where a name is said in the line, as word positions."""
        n = len(name)
        return [(k, k + n) for k in range(len(rest) - n + 1) if rest[k:k + n] == name] if n else []

    found = []
    for t in targets:
        name = name_words(t["label"])
        own = spans(name)
        if not own:
            continue
        ups = [name_words(u) for u in t.get("up") or []]
        # "open apply for a loan" names the page; the form's tab "Loan" is only a word of that name. A name that
        # is said nowhere but inside a longer name above it is not what the line names
        above = [sp for u in ups if len(u) > len(name) for sp in spans(u)]
        if all(any(x <= k and e <= y for x, y in above) for k, e in own):
            continue
        known = {w[:4] for w in name} | {w[:4] for u in ups for w in u}
        if any(len(w) >= 4 and w[:4] not in known for w in rest):
            continue                              # a word of weight that is neither this name nor its way
        way = sum(1 for u in ups if u and " " + " ".join(u) + " " in said)
        found.append((way, 1 if t.get("here") else 0, 1 if t["kind"] == "page" else 0, len(name), t["id"]))
    if found:
        found.sort(reverse=True)
        top = [f for f in found if f[:4] == found[0][:4]]
        return (found[0][4], "said") if len({f[4] for f in top}) == 1 else None
    hit = match_name(phrase, [(t["id"], t["label"], t["kind"]) for t in targets])
    return (hit[0], "near") if hit and not hit[2] else None


_MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})


def spoken_date(phrase: str) -> str | None:
    """A whole date said or typed with nothing else of weight around it, as YYYY-MM-DD: "1st July 2014", "July 1,
    2014", "the first of July 2014" is not read (a day in words is the agent's), "01.07.2014", "2014-07-01".
    None when the line is not a bare date."""
    text = (phrase or "").lower().strip()
    m = re.fullmatch(r"\W*(\d{4})-(\d{1,2})-(\d{1,2})\W*", text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"\W*(\d{1,2})[./](\d{1,2})[./](\d{4})\W*", text)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            words = [w for w in re.findall(r"[a-z]+|\d+", re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", text))
                     if w not in _AROUND and w not in ("of", "on", "it's", "its", "is", "born", "date")]
            nums = [int(w) for w in words if w.isdigit()]
            months = [_MONTHS[w] for w in words if w in _MONTHS]
            if len(words) != 3 or len(nums) != 2 or len(months) != 1:
                return None
            y = next((n for n in nums if n > 31), 0)
            d = next((n for n in nums if n <= 31), 0)
            mo = months[0]
    import datetime
    try:
        return datetime.date(y, mo, d).isoformat() if y >= 1900 else None
    except ValueError:
        return None


_DATE_IN = re.compile(
    r"\b(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m>[a-z]{3,9})\.?,?\s+(?P<y>\d{4}|['\u2019]?\d{2})\b"
    r"|\b(?P<m2>[a-z]{3,9})\.?\s+(?P<d2>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<y2>\d{4}|['\u2019]?\d{2})\b"
    r"|\b(?P<d3>\d{1,2})[./](?P<m3>\d{1,2})[./](?P<y3>\d{4})\b|\b(?P<y4>\d{4})-(?P<m4>\d{1,2})-(?P<d4>\d{1,2})\b")


def date_in(phrase: str) -> tuple[str | None, str]:
    """A whole date said inside a line, as YYYY-MM-DD, and the line without it: "Lugansk, 1st July '92" ->
    ("1992-07-01", "Lugansk, "). A year of two digits is this century when it is not ahead of now, else the last
    one. (None, the line) when the line holds no whole date."""
    import datetime
    text = phrase or ""
    for m in _DATE_IN.finditer(text.lower()):
        g = m.groupdict()
        d, mo, y = (g["d"] or g["d2"] or g["d3"] or g["d4"]), (g["m"] or g["m2"] or g["m3"] or g["m4"]), (g["y"] or g["y2"] or g["y3"] or g["y4"])
        month = int(mo) if mo.isdigit() else _MONTHS.get(mo) or _MONTHS.get(mo[:3])
        if not month:
            continue
        y = y.lstrip("'\u2019")
        year = int(y)
        if len(y) == 2:
            year += 2000 if year <= datetime.date.today().year % 100 else 1900
        try:
            iso = datetime.date(year, month, int(d)).isoformat() if year >= 1900 else None
        except ValueError:
            iso = None
        if iso:
            return iso, text[:m.start()] + " " + text[m.end():]
    return None, text


_DAY_THEN_MONTH = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]{3,9})\b")
_MONTH_THEN_DAY = re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b")


def partial_date(phrase: str) -> tuple[int, int] | None:
    """(day, month) of a date said without its year ("born on the 1st of July"), or None: no day and month in the
    line, or the line holds a whole date."""
    if date_in(phrase)[0] or spoken_date(phrase):
        return None
    low = (phrase or "").lower()
    found = [(m.group(1), m.group(2)) for m in _DAY_THEN_MONTH.finditer(low)] + [(m.group(2), m.group(1)) for m in _MONTH_THEN_DAY.finditer(low)]
    for d, mo in found:
        month = _MONTHS.get(mo) or (_MONTHS.get(mo[:3]) if len(mo) == 3 else None)
        if month and 1 <= int(d) <= 31:
            return int(d), month
    return None


def bare_year(phrase: str) -> int | None:
    """The year when the line is nothing but a year ("1991", "uh, 1991."), else None."""
    words = [w for w in re.findall(r"[a-z]+|\d+", (phrase or "").lower()) if w not in _AROUND and w not in ("in", "year", "the", "it", "was", "its")]
    return int(words[0]) if len(words) == 1 and words[0].isdigit() and 1900 <= int(words[0]) <= 2100 else None


def only_names(phrase: str, label: str) -> bool:
    """Whether the line is nothing but the place's name, with fillers at most ("contacts", "uh, the contacts"): no
    verb of an order, no other word. "Open contacts" is not: it says what to do."""
    own = {w[:4] for w in re.findall(r"[\w']+", (label or "").lower())}
    words = [w for w in re.findall(r"[\w']+", (phrase or "").lower()) if w not in _AROUND]
    return bool(words) and all(w[:4] in own for w in words)


# a day and a month as people write them, and "Which year?", in the chat's languages (Head of Design, 2026-11-17:
# a plain sentence, the month as a word, the day without a leading zero; never a mask like "01.07.____")
_MONTH_NAMES = {
    "en": "January February March April May June July August September October November December".split(),
    "ru": "\u044f\u043d\u0432\u0430\u0440\u044f \u0444\u0435\u0432\u0440\u0430\u043b\u044f \u043c\u0430\u0440\u0442\u0430 \u0430\u043f\u0440\u0435\u043b\u044f \u043c\u0430\u044f \u0438\u044e\u043d\u044f \u0438\u044e\u043b\u044f \u0430\u0432\u0433\u0443\u0441\u0442\u0430 \u0441\u0435\u043d\u0442\u044f\u0431\u0440\u044f \u043e\u043a\u0442\u044f\u0431\u0440\u044f \u043d\u043e\u044f\u0431\u0440\u044f \u0434\u0435\u043a\u0430\u0431\u0440\u044f".split(),
    "uk": "\u0441\u0456\u0447\u043d\u044f \u043b\u044e\u0442\u043e\u0433\u043e \u0431\u0435\u0440\u0435\u0437\u043d\u044f \u043a\u0432\u0456\u0442\u043d\u044f \u0442\u0440\u0430\u0432\u043d\u044f \u0447\u0435\u0440\u0432\u043d\u044f \u043b\u0438\u043f\u043d\u044f \u0441\u0435\u0440\u043f\u043d\u044f \u0432\u0435\u0440\u0435\u0441\u043d\u044f \u0436\u043e\u0432\u0442\u043d\u044f \u043b\u0438\u0441\u0442\u043e\u043f\u0430\u0434\u0430 \u0433\u0440\u0443\u0434\u043d\u044f".split(),
    "it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(),
    "de": "Januar Februar M\xe4rz April Mai Juni Juli August September Oktober November Dezember".split(),
    "fr": "janvier f\xe9vrier mars avril mai juin juillet ao\xfbt septembre octobre novembre d\xe9cembre".split(),
    "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
}
_WHICH_YEAR = {"en": "Which year?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u0433\u043e\u0434?", "uk": "\u042f\u043a\u0438\u0439 \u0440\u0456\u043a?", "it": "Che anno?", "de": "Welches Jahr?", "fr": "Quelle ann\xe9e ?", "es": "\xbfQu\xe9 a\xf1o?"}
_DAY_MONTH_SHAPE = {"en": "{m} {d}", "de": "{d}. {m}", "es": "{d} de {m}"}   # the others: "{d} {m}"


def ask_the_year(label: str, day: int, month: int, language: str | None) -> str:
    """"Date of birth: 1 July. Which year?" in the chat's language (English when it is not one of ours)."""
    lang = language if language in _MONTH_NAMES else "en"
    date = _DAY_MONTH_SHAPE.get(lang, "{d} {m}").format(d=day, m=_MONTH_NAMES[lang][month - 1])
    return f"{label}: {date}. {_WHICH_YEAR[lang]}"


def says_more(rest: str) -> bool:
    """Whether what is left of a line, beside the value read from it, still says something: a word of three
    letters or more that is not a filler or a word of an order."""
    return any(len(w) >= 3 and w not in _AROUND and w not in _ORDER_WORDS and w not in ("born", "date", "birth", "its", "was")
               for w in re.findall(r"[a-z\u00c0-\u024f\u0400-\u04ff']+", (rest or "").lower()))


_LONG_DIGITS = re.compile(r"\d[\d\s().-]{5,}\d")


async def choose_on_screen(layer: "Layer", what: str, options: list[Option], language: str = "en",
                           screen: str = "") -> dict[str, Any]:
    """The tool an agent calls: rank the screen's options for a target the model named, and say what may be done
    with the answer. Never acts; the caller acts on "pick" when the person's own line allows it.
        {"status": "pick", "id", "label", "confidence"}           the first option, sure and clear of the second
        {"status": "candidates", "options": [labels, 5 at most]}   two fit, or one fits without being sure
        {"status": "not_found"} | {"status": "too_many"} | {"status": "unavailable", "why"}
    """
    s = layer.settings
    what = (what or "").strip()
    if not layer.on:
        return {"status": "unavailable", "why": "off"}
    if not what or layer.private(what) or _LONG_DIGITS.search(what):
        return {"status": "unavailable", "why": "private"}      # a phone, an e-mail, a long number: it stays here
    options = [o for o in options if not layer.private(o.label)]
    if not options:
        return {"status": "not_found"}
    if len(options) > MAX_OPTIONS - 1:
        return {"status": "too_many"}
    question = Question("choice", "target", "Which of these is the one the line names?", tuple(options), act="show")
    try:
        ranked = await asyncio.wait_for(layer.chooser.rank(what, language, question, screen), s.timeout_ms / 1000)
    except Exception:  # noqa: BLE001 - late, failed, or a chooser that cannot rank
        return {"status": "unavailable", "why": "late"}
    by_id = {o.id: o for o in options}
    ranked = sorted(((i, float(p)) for i, p in (ranked or []) if i in by_id), key=lambda x: -x[1])
    if not ranked or ranked[0][1] < s.threshold:
        return {"status": "not_found"}
    (top, p1), p2 = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0.0)
    if p1 >= s.act and p1 - p2 >= s.margin:
        return {"status": "pick", "id": top, "label": by_id[top].label, "confidence": p1}
    fit = [by_id[i].label for i, p in ranked if p >= min(s.threshold, p1 / 2)][:5]
    return {"status": "candidates", "options": fit or [by_id[top].label]}


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
