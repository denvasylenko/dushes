"""The conversation's language, and cards in it.

The main path needs no model: the host or the form sets `language`, the form carries its own translations
(`props[field].i18n[lang].label`, an option's `names[lang]`) and the widget has its language packs. Only when no
language is set is it detected from the user's messages, and only strings the form does not translate go to a
cheap model (one batched call, cached; `translate_missing: false` turns it off). The values sent to the form
never change, and a failed translation never holds a card back.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from .form.layout import CHOICE

log = logging.getLogger("formguide.language")

LANGS = ("en", "ru", "uk", "de", "fr", "es", "it")
NAMES = {"en": "English", "ru": "Russian", "uk": "Ukrainian", "de": "German", "fr": "French", "es": "Spanish",
         "it": "Italian"}
TIMEOUT = 2.0

# a few everyday words of each language (non-ASCII letters as escapes: the repository is English-only)
_WORDS = {
    "en": {"the", "and", "of", "to", "is", "in", "for", "you", "my", "by", "with", "this", "what", "how", "please",
           "want", "need", "it", "on", "are", "do", "can", "your", "which", "would", "like", "have", "was", "that"},
    "de": {"der", "die", "das", "und", "ich", "ist", "nicht", "ein", "eine", "f\u00fcr", "mit", "es", "von", "mein",
           "m\u00f6chte", "bitte", "wie", "was", "auf", "zu", "den", "im", "wir", "sie", "haben", "welche", "oder"},
    "fr": {"le", "les", "et", "je", "est", "une", "pour", "avec", "mon", "des", "du", "que", "pas", "vous",
           "bonjour", "ce", "dans", "sur", "voudrais", "quel", "quelle", "nous", "merci", "au"},
    "es": {"el", "los", "las", "y", "para", "mi", "que", "por", "quiero", "hola", "no", "se", "como", "una", "es",
           "necesito", "cual", "tengo", "gracias", "del", "con"},
    "it": {"il", "lo", "gli", "e", "\u00e8", "per", "mio", "mia", "che", "non", "vorrei", "ciao", "di", "del",
           "della", "sono", "come", "una", "grazie", "quale", "ho", "con"},
}
_MARKS = {"de": "\u00e4\u00f6\u00fc\u00df", "es": "\u00f1\u00bf\u00a1", "fr": "\u00e7\u0153\u00ea\u00e2\u00ee",
          "it": "\u00f2\u00f9\u00ec"}
_UK = "\u0456\u0457\u0454\u0491"            # Ukrainian letters that Russian does not have
_RU = "\u044b\u044d\u044a\u0451"            # Russian letters that Ukrainian does not have


def norm(lang: Any) -> str | None:
    """'de-DE' -> 'de'; None for a language we do not know."""
    code = str(lang or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in LANGS else None


def detect(text: str | None) -> str | None:
    """The language of a text, or None when it is too short or mixed to say."""
    t = (text or "").lower()
    cyr = sum("\u0400" <= c <= "\u04ff" for c in t)
    lat = sum("a" <= c <= "z" for c in t)
    if cyr > lat and cyr >= 3:
        if any(c in t for c in _UK) and not any(c in t for c in _RU):
            return "uk"
        return "ru"
    words = re.findall(r"[^\W\d_]+", t)
    if not words:
        return None
    score = {lang: sum(w in known for w in words) + 2 * any(c in t for c in _MARKS.get(lang, ""))
             for lang, known in _WORDS.items()}
    ranked = sorted(score.items(), key=lambda kv: -kv[1])
    top, second = ranked[0], ranked[1]
    return top[0] if top[1] >= 2 and top[1] > second[1] else None


def conversation(config: Any, form_props: dict[str, Any] | None, message: str | None, before: str | None) -> str | None:
    """The language cards are shown in: the form's `language`, else the host's, else the one the message is
    written in (kept to the host's `languages` when set), else what the conversation used before."""
    fixed = norm((form_props or {}).get("language")) or norm(getattr(config, "language", None))
    if fixed:
        return fixed
    allowed = [x for x in (norm(a) for a in getattr(config, "languages", None) or []) if x]
    found = detect(message)
    if found and allowed and found not in allowed:
        found = None
    return found or before or (allowed[0] if allowed and not before else None)


def source(ov: Any) -> str:
    """The language the form's own labels are written in (English when it cannot be told)."""
    labels = " ".join(str(e.label) for e in ov.eff.values() if e.label)[:4000]
    return detect(labels) or "en"


def form_label(e: Any, lang: str) -> str | None:
    """The form's own translation of a field's label, if it has one."""
    own = ((e.props.get("i18n") or {}).get(lang) or {}) if isinstance(e.props.get("i18n"), dict) else {}
    return str(own["label"]) if isinstance(own, dict) and own.get("label") else None


def option_name(o: dict[str, Any], lang: str) -> str | None:
    """The form's own translation of an option's name, if it has one."""
    raw = o.get("raw") if isinstance(o.get("raw"), dict) else o
    names = raw.get("names") if isinstance(raw, dict) else None
    return str(names[lang]) if isinstance(names, dict) and names.get(lang) else None


class Translator:
    """Strings the form does not translate: one batched call to a cheap model, remembered per language."""

    def __init__(self) -> None:
        self.cache: dict[tuple[str, str], str] = {}

    async def translate(self, model: Any, lang: str, texts: list[str], stats: Any = None) -> dict[str, str]:
        out = {t: self.cache[(lang, t)] for t in texts if (lang, t) in self.cache}
        todo = [t for t in dict.fromkeys(texts) if t not in out and t.strip()]
        if not todo or model is None:
            return out
        from langchain_core.messages import HumanMessage, SystemMessage

        from .stats import RunStats, model_id
        started = RunStats.now()
        usage = None
        try:
            res = await asyncio.wait_for(model.ainvoke([
                SystemMessage(content=(
                    f"Translate each string of the JSON array to {NAMES[lang]} for a form's interface: short and "
                    "natural. Keep numbers, names, codes and anything already in that language as they are. "
                    "Answer with a JSON array of the same length and order, nothing else.")),
                HumanMessage(content=json.dumps(todo, ensure_ascii=False))]), TIMEOUT)
            usage = dict(getattr(res, "usage_metadata", None) or {}) or None
            text = res.content if isinstance(res.content, str) else " ".join(
                b.get("text", "") for b in res.content if isinstance(b, dict))
            got = json.loads(text[text.index("["): text.rindex("]") + 1])
            if isinstance(got, list) and len(got) == len(todo):
                for src, dst in zip(todo, got):
                    if isinstance(dst, str) and dst.strip():
                        self.cache[(lang, src)] = out[src] = dst.strip()
        except Exception as e:  # noqa: BLE001 - a card is never held back by a translation
            log.info("card translation skipped: %s", type(e).__name__)
        if stats is not None:
            stats.model_call(started, None, usage, kind="translate", model=model_id(model))
        return out


async def localize(pending: dict[str, Any], ov: Any, lang: str | None, *, translator: Translator | None = None,
                   model: Any = None, stats: Any = None) -> None:
    """Put a waiting card (the graph's `pending`) into the conversation's language, in place: the form's own
    translations first, then one model call for the rest. Values sent to the form are not touched."""
    if not lang:
        return
    src = source(ov)
    spots: list[tuple[dict, str, bool]] = []   # (holder, key, the form's own words)

    def field(name: Any) -> Any:
        return ov.get(str(name)) if name is not None else None

    def label_of(holder: dict, key: str, e: Any) -> None:
        text = holder.get(key)
        if not isinstance(text, str) or not text.strip():
            return
        own = e is not None and text == (e.label or e.name)
        if own and form_label(e, lang):
            holder[key] = form_label(e, lang)
            return
        spots.append((holder, key, own))

    def option(holder: dict, key: str, e: Any) -> None:
        text = holder.get(key)
        if not isinstance(text, str) or not text.strip():
            return
        match = next((o for o in (e.options or []) if o.get("name") == text), None) if e is not None else None
        if match is not None and option_name(match, lang):
            holder[key] = option_name(match, lang)
            return
        spots.append((holder, key, match is not None))

    def said(holder: dict, key: str) -> None:
        if isinstance(holder.get(key), str) and holder[key].strip():
            spots.append((holder, key, False))

    if pending.get("kind") == "set_fields":
        for row in pending.get("changes") or []:
            e = field(row.get("name"))
            label_of(row, "label", e)
            said(row, "reason")
            if isinstance(row.get("issue"), dict):
                said(row["issue"], "message")
            if e is not None and (e.node.role in CHOICE or row.get("deferred")):
                option(row, "display", e)
        pending["language"] = lang
    else:
        p = pending.get("payload") or {}
        e = field(p.get("field"))
        for key in ("question", "message", "title", "prompt", "consequence"):
            said(p, key)
        for o in p.get("options") or []:
            if isinstance(o, dict):
                option(o, "label", e)
                said(o, "description")
        for f in p.get("fields") or []:
            if isinstance(f, dict):
                label_of(f, "label", field(f.get("name")))
        p["language"] = lang

    need = []
    for holder, key, own in spots:
        found = detect(holder[key])
        if (found and found != lang) or (found is None and own and src != lang):
            need.append((holder, key))
    if not need or translator is None:
        return
    done = await translator.translate(model, lang, [h[k] for h, k in need], stats)
    for holder, key in need:
        if holder[key] in done:
            holder[key] = done[holder[key]]
