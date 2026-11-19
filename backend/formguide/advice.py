"""`formguide check`: what is weak in a host's own description of its site and forms, and how to fix each thing.

No model is called and nothing leaves the machine: the checks read the configuration, the site map, a form's layout
with a sample of its config, the domain pack, the list of documents and the process's environment. Each finding
says where, what, and what to write instead. An "error" is something that will hurt a person's data or a public
host; a "warning" makes the agents understand or answer worse; a "note" is worth knowing.

A check that needs a judgement about words (which language a keyword is in, whether a label reads well to a
person) is made by a plain rule and says so; it never claims more than the rule can know.
"""
from __future__ import annotations

import dataclasses
import re
from typing import Any

LEVELS = ("error", "warning", "note")

# names and labels that suggest a field holds something personal: a hint for the host to mark it, never a decision
# (matched against the whole words of the field's name and label, never inside a word. A phone and an e-mail are
# clear enough to be an error; a document or a bank detail may belong to a company, so it is a warning to look at)
_PERSONAL = {
    "a phone number": ("error", {"phone", "tel", "mobile", "cell", "telefon", "handy", "whatsapp"}),
    "an e-mail address": ("error", {"email", "mail"}),
    "an identity document": ("warning", {"passport", "ssn", "snils", "inn", "ausweis", "licence", "license"}),
    "a bank detail": ("warning", {"iban", "cvv", "cvc"}),
}
# the same for categories a law treats as special: such a field should be kept out of everything
_SPECIAL = ("health", "medical", "diagnos", "disabil", "religio", "ethnic", "race", "union", "biometr", "criminal",
            "convict", "sexual", "pregnan", "allerg", "diet")
# switches that show a person how a turn was decided: for the owner's own eyes, never for a public host
_FOR_THE_OWNER_ONLY = ("INTENT_LABELS", "INTENT_TRACE", "INTENT_SCORES")


@dataclasses.dataclass(frozen=True)
class Finding:
    level: str     # one of LEVELS
    where: str     # "site /loans", "form loan_application: phone_mobile", "environment"
    what: str      # what is weak, and what follows from it
    fix: str       # what to write or set


def _words(text: Any) -> list[str]:
    return re.findall(r"[^\W\d_]+", str(text or "").lower())


def _technical(label: str, name: str) -> bool:
    """A label a person would not say: empty, the field's own name, or written like an identifier."""
    text = (label or "").strip()
    if not text or text == name:
        return True
    return " " not in text and ("_" in text or bool(re.search(r"[a-z][A-Z]", text)) or bool(re.search(r"\d", text) and text.islower()))


def check_site(site: Any, languages: list[str] | None, documents_for: Any = None, packs: Any = None) -> list[Finding]:
    """The site map: keywords in the site's languages, titles two places share, forms with no documents."""
    out: list[Finding] = []
    langs = [x for x in (languages or []) if x]
    titles: dict[str, list[str]] = {}
    for page in site.pages:
        where = f"site {page.path}"
        titles.setdefault(" ".join(_words(page.title)), []).append(page.path)
        for part in page.parts:
            titles.setdefault(" ".join(_words(part.title)), []).append(f"{page.path}#{part.id}")
        if not page.keywords:
            out.append(Finding("warning", where, f'"{page.title}" has no keywords: a visitor who calls it by another word, '
                               "or in another language, is not understood by the choice model",
                               "add `keywords:` with the words visitors use for this page, in every language they speak"))
        elif len(langs) > 1 and len(page.keywords) < len(langs):
            out.append(Finding("warning", where, f"{len(page.keywords)} keyword(s) for a site in {len(langs)} languages "
                               f"({', '.join(langs)}): a capitalised word of a visitor's line that is not a title or a "
                               "keyword is hidden from the choice model as a likely name (in German every noun is one)",
                               "write at least one keyword for this page in each of the site's languages "
                               "(this check counts them; it cannot tell which language a keyword is in)"))
        if page.form:
            pack = packs.get(page.form) if packs is not None else None
            docs = list(documents_for(page.form)) if documents_for is not None else None
            if docs is not None and not docs:
                out.append(Finding("note", where, f'the form "{page.form}" has no business documents: asked about '
                                   "conditions, prices or rules the agent answers from the form alone and says there "
                                   "are no documents", f"add documents for {page.form} (POST /kb/{page.form}/documents)"))
            if pack is not None and getattr(pack, "source", "") == "default":
                out.append(Finding("warning", where, f'the form "{page.form}" has no domain pack: the agent has a neutral '
                                   "persona, no notes on fields and no list of personal fields",
                                   f"write a pack for {page.form} (title, glossary, pii, rules)"))
    for key, places in titles.items():
        if key and len(places) > 1:
            out.append(Finding("warning", "site", f'the same title "{key}" names {len(places)} places ({", ".join(places)}): '
                               "asked to open it, the choice model wavers between them and the person is asked which",
                               "give each place its own title, or tell them apart with keywords"))
    if not any(p.keywords for p in site.pages) and site.pages:
        out.append(Finding("note", "site", "no page has keywords at all", "start with the pages visitors ask for most"))
    return out


def check_form(form_id: str, layout: Any, config: dict[str, Any], pack: Any) -> list[Finding]:
    """One form with a sample of its config: labels and options a person can read, personal fields the pack does not
    mark, required fields with no note that says why."""
    from .form.overlay import Overlay
    out: list[Finding] = []
    ov = Overlay(layout, config, set(getattr(pack, "pii", None) or ()))
    pii = set(getattr(pack, "pii", None) or ()) | set(getattr(pack, "special", None) or ())
    glossary = getattr(pack, "glossary", None) or {}
    unexplained: list[str] = []
    for node in layout.fields():
        if node.template:        # a row's field: its template is checked once
            continue
        e = ov.get(node.name)
        if e is None or e.missing:
            continue
        where, label = f"form {form_id}: {node.name}", str(e.label or "")
        if _technical(label, node.name):
            out.append(Finding("warning", where, (f'the label "{label}" reads like an identifier' if label else "no label")
                               + ": the agents name this field to the person by its label, and match what the person "
                               "says against it", f'give {node.name} a label a person would say ("Mobile phone")'))
        bad = [str(o.get("id")) for o in e.opts or [] if not str(o.get("name") or "").strip() or str(o.get("name")) == str(o.get("id")) and _technical(str(o.get("name")), "")]
        if bad:
            out.append(Finding("warning", where, f"{len(bad)} option(s) have no readable name ({', '.join(bad[:5])}): the "
                               "person is shown and asked for the id", "give every option a name to show beside its id"))
        said = {*_words(node.name.replace("_", " ")), *_words(label)}
        if node.name not in pii and node.role != "file":
            for kind, (level, hints) in _PERSONAL.items():
                if said & hints:
                    out.append(Finding(level, where, f"looks like {kind} and the pack does not mark it personal: its "
                                       "value is shown to the model and may go to the choice model's supplier",
                                       f"add {node.name} to the pack's `pii` (the check goes by the words of the "
                                       "field's name and label; if it is not a person's, leave it)"))
                    break
            if any(w.startswith(h) for w in said for h in _SPECIAL):
                out.append(Finding("error", where, "sounds like a special category of personal data (health, religion and "
                                   "the like) and the pack does not mark it", f"add {node.name} to the pack's `pii`"))
        if e.props.get("required") and node.role != "bool" and node.name not in glossary:
            unexplained.append(node.name)
    if unexplained:
        out.append(Finding("note", f"form {form_id}", f"{len(unexplained)} required field(s) have no note in the pack's glossary "
                           f"({', '.join(unexplained[:8])}{'…' if len(unexplained) > 8 else ''}): asked why it is needed, "
                           "the agent can only guess", "add a one-line note per field to `glossary` for the ones people ask about"))
    return out


def check_defaults(cfg: Any, site: Any = None) -> list[Finding]:
    """What a host gets weaker by default than it probably expects, each with the line to paste. Read from the
    loaded configuration; what lives in the host's own Python (the site agent's arguments) cannot be seen from
    here, so it is said as a thing to look at."""
    out: list[Finding] = []
    if getattr(cfg, "checkpointer", None) is None:
        out.append(Finding("warning", "formguide.yaml: checkpointer", "the UI agent's conversation state is kept in memory: "
                           "after a restart, or on a second instance, it has forgotten the conversation",
                           "add `checkpointer: {sqlite: data/checkpoints.sqlite}` (or pass a Postgres or Redis saver in Python)"))
    suggestions = getattr(cfg, "suggestions", None)
    if suggestions is not None and not getattr(suggestions, "enabled", False):
        out.append(Finding("note", "formguide.yaml: suggestions", "quick replies under an answer are off",
                           "add `suggestions: {enabled: true, max: 3}`; for the site agent also `Dushes(..., suggestions=True)`"))
    if site is not None and any(p.form for p in site.pages):
        out.append(Finding("note", "your code: Dushes(...)", "the site has pages with forms: without `form_for` a form's first "
                           "turn waits for its page to load, and the decision model does not see another page's form "
                           "(this check cannot read your Python, so it only reminds)",
                           "pass `form_for=` a function (form_id, ctx) that returns the form's {config, jsx_hash, form_id}"))
    return out


def check_environment(env: dict[str, str], public: bool) -> list[Finding]:
    """The process's switches: what must not be on for a public host, and what is on with nobody let in."""
    out: list[Finding] = []
    shown = [k for k in _FOR_THE_OWNER_ONLY if env.get(k) == "1"]
    if shown:
        out.append(Finding("error" if public else "warning", "environment", f"{', '.join(shown)} show every person how their "
                           "turn was decided (the model's name, its numbers, the masked line)",
                           "unset them on a public host; they are for the owner's own demo"))
    if env.get("DEMO_SHOW_CONFIG") == "1" and public:
        out.append(Finding("error", "environment", "DEMO_SHOW_CONFIG=1 publishes this host's configuration, packs, "
                           "documents and every prompt to anyone who asks", "unset it on a public host; show a "
                           "snapshot built from the repository's files instead, checked for secrets before it ships"))
    if env.get("INTENT_PROVIDER") and not env.get("EXPERIMENT_CODES") and public:
        out.append(Finding("warning", "environment", "the choice layer is on (INTENT_PROVIDER) and no access codes are set: "
                           "every visitor's lines go to its supplier", "set EXPERIMENT_CODES so it runs only for people "
                           "with a code, or decide per run with the host's `layer` argument"))
    if env.get("INTENT_PROVIDER") and not env.get("INTENT_API_KEY"):
        out.append(Finding("warning", "environment", "INTENT_PROVIDER is set without INTENT_API_KEY: the choice layer will "
                           "not answer and every line goes to the model", "set the key, or unset the provider"))
    if (env.get("OPENAI_API_KEY") or env.get("VOICE_MODEL")) and not env.get("VOICE_CODES") and env.get("VOICE_SECRET"):
        out.append(Finding("warning", "environment", "a voice secret is set without VOICE_CODES: voice stays off",
                           "set VOICE_CODES (name:code pairs) for the people who may talk"))
    if env.get("VOICE_CODES") and not env.get("VOICE_SECRET") and public:
        out.append(Finding("warning", "environment", "VOICE_CODES without VOICE_SECRET: passes do not survive a restart "
                           "and differ between instances", "set VOICE_SECRET to one long random value"))
    if env.get("JOURNAL") == "1" and public:
        out.append(Finding("note", "environment", "the decision journal is on: it is personal data kept for up to 30 days",
                           "say so in the privacy notice, and keep its folder outside snapshots (JOURNAL_DIR)"))
    return out


def render(findings: list[Finding]) -> str:
    if not findings:
        return "nothing weak found"
    lines = []
    for level in LEVELS:
        for f in (x for x in findings if x.level == level):
            lines.append(f"{level.upper():7} {f.where}\n        {f.what}\n        fix: {f.fix}")
    counts = ", ".join(f"{sum(1 for f in findings if f.level == lv)} {lv}(s)" for lv in LEVELS if any(f.level == lv for f in findings))
    return "\n".join(lines) + f"\n{counts}"
