"""The conversation's language: set or detected; cards in it from the form's translations, else a cheap model."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from formguide.language import Translator, conversation, detect

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN, interrupt_value

DE = "Ich m\u00f6chte ein Angebot f\u00fcr mein Auto. Es ist ein Honda Civic von 2019."
RU = "\u0425\u043e\u0447\u0443 \u043a\u0440\u0435\u0434\u0438\u0442 \u043d\u0430 \u043c\u0430\u0448\u0438\u043d\u0443"   # Russian: I want a car loan


class FakeTranslator:
    """Stands in for the cheap model: every string comes back marked with the language."""

    def __init__(self):
        self.calls = []

    async def ainvoke(self, msgs):
        texts = json.loads(msgs[-1].content)
        self.calls.append(texts)
        return AIMessage(content=json.dumps([f"<{t}>" for t in texts]),
                         usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})


def test_detect_knows_the_seven_languages_and_stays_silent_when_unsure():
    assert detect(DE) == "de" and detect(RU) == "ru" and detect("I want a loan for my car, please") == "en"
    assert detect("Vorrei un preventivo per la mia auto, grazie") == "it"
    assert detect("Je voudrais un devis pour mon v\u00e9hicule, merci") == "fr"
    assert detect("Hola, quiero un pr\u00e9stamo para mi coche, gracias") == "es"
    assert detect("\u0425\u043e\u0447\u0443 \u043a\u0440\u0435\u0434\u0438\u0442 \u043d\u0430 \u0430\u0432\u0442\u043e\u043c\u043e\u0431\u0456\u043b\u044c") == "uk"   # Ukrainian
    assert detect("ok") is None and detect("Honda Civic 2019") is None and detect("") is None


def test_a_set_language_is_not_guessed():
    cfg = SimpleNamespace(language="it", languages=None)
    assert conversation(cfg, None, DE, None) == "it"
    assert conversation(SimpleNamespace(language=None, languages=None), {"language": "ru"}, DE, None) == "ru"   # the form's
    free = SimpleNamespace(language=None, languages=None)
    assert conversation(free, None, DE, "en") == "de" and conversation(free, None, "ok", "de") == "de"
    only = SimpleNamespace(language=None, languages=["en", "it"])
    assert conversation(only, None, DE, None) == "en"             # German is not offered: the default


def _ask(guide, model, thread, message, state=None):
    model.script = [say("", ("q1", "ask_user", {"question": "Which loan type do you need?", "field": "loan_type"}))]
    ev = collect(guide, thread, message=message, state=state or start(guide, LOAN))
    return ev, interrupt_value(ev)


def test_a_card_is_translated_once_and_counted(guide, model):
    fake = FakeTranslator()
    guide.config.translate_missing, guide.translation_model = True, fake
    ev, v = _ask(guide, model, "lg1", DE)
    assert v["language"] == "de" and v["question"] == "<Which loan type do you need?>"
    assert all(o["label"].startswith("<") for o in v["options"])                     # the form's English names
    assert {o["id"] for o in v["options"]} >= {"consumer", "mortgage"}               # the values stay the form's
    assert [e["value"] for e in ev if e.get("name") == "language"] == [{"lang": "de"}]
    stats = next(e["value"] for e in ev if e.get("name") == "run_stats")
    assert [m["kind"] for m in stats["models"]].count("translate") == 1
    _ask(guide, model, "lg2", DE)
    assert len(fake.calls) == 1                                                       # remembered: no second call
    assert guide.thread("lg1")["language"] == "de"


def test_the_forms_own_translations_need_no_model(guide, model):
    fake = FakeTranslator()
    guide.config.translate_missing, guide.translation_model = True, fake
    state = start(guide, LOAN)
    props = state["config"]["props"]
    props["loan_type"] = {**props["loan_type"], "i18n": {"de": {"label": "Kreditart"}},
                          "options": [{**o, "names": {"de": f"DE {o['name']}"}} for o in props["loan_type"]["options"]]}
    model.script = [say("", ("q1", "ask_user", {"question": "Welche Kreditart brauchen Sie f\u00fcr das Auto?",
                                                "field": "loan_type"}))]
    v = interrupt_value(collect(guide, "lg3", message=DE, state=state))
    assert all(o["label"].startswith("DE ") for o in v["options"]) and fake.calls == []
    model.script = [say("", ("c1", "propose_changes", {"changes": [{"name": "loan_type", "value": "consumer"}]}))]
    v = interrupt_value(collect(guide, "lg4", message=DE, state=state))
    row = v["changes"][0]
    assert row["label"] == "Kreditart" and row["display"].startswith("DE ") and row["value"]["id"] == "consumer"


def test_without_translate_missing_the_forms_words_show(guide, model):
    fake = FakeTranslator()
    guide.translation_model = fake                                   # translate_missing is off in this fixture
    _, v = _ask(guide, model, "lg5", DE)
    assert v["question"] == "Which loan type do you need?" and fake.calls == [] and v["language"] == "de"


def test_a_failed_translation_never_holds_the_card(guide, model):
    class Broken:
        async def ainvoke(self, msgs):
            raise RuntimeError("down")
    guide.config.translate_missing, guide.translation_model = True, Broken()
    _, v = _ask(guide, model, "lg6", DE)
    assert v["question"] == "Which loan type do you need?"
    got = asyncio.run(Translator().translate(Broken(), "de", ["Skip"]))
    assert got == {}


def test_an_english_conversation_costs_nothing(guide, model):
    fake = FakeTranslator()
    guide.config.translate_missing, guide.translation_model = True, fake
    _, v = _ask(guide, model, "lg7", "I want a loan for my car, please")
    assert v["question"] == "Which loan type do you need?" and fake.calls == [] and v["language"] == "en"


def test_a_fill_card_in_german_keeps_the_value(guide, model):
    fake = FakeTranslator()
    guide.config.translate_missing, guide.translation_model = True, fake
    model.script = [say("", ("c1", "propose_changes", {"changes": [
        {"name": "last_name", "value": "Morozova", "reason": "Given by the user in the chat"}]}))]
    row = interrupt_value(collect(guide, "lg8", message=DE, state=start(guide, LOAN)))["changes"][0]
    assert row["label"].startswith("<") and row["reason"] == "<Given by the user in the chat>"   # label and note
    assert row["value"] == "Morozova" and row["display"] == "Morozova"                            # never the value
