"""The form agent reads what the page around its form says (page facts)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from formguide.agent.prompts import CORE, page_facts
from formguide.site import Dushes, SiteMap

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN

SITE = Path(__file__).resolve().parents[1] / "demo" / "site.yaml"
PAGE = {"title": "Vehicle registration", "description": "Register a car online.",
        "sections": [{"title": "Fees", "text": "Registration costs 27.90 EUR."}, {"title": "Empty", "text": ""}]}


def _last(model):
    last = model.calls[-1][-1].content
    return last if isinstance(last, str) else " ".join(b.get("text", "") for b in last if isinstance(b, dict))


def test_the_block_holds_the_page_and_is_cut():
    block = page_facts(PAGE)
    assert block.startswith('<page_facts page="Vehicle registration">') and "Fees: Registration costs 27.90 EUR." in block
    assert "Empty" not in block and page_facts(None) == "" and page_facts({"title": "x"}) == ""
    long = page_facts({"sections": [{"title": "T", "text": "a" * 9000}]})
    assert len(long) < 4200 and "(cut)" in long
    assert "never say the form or the page does not give a fact that it holds" in " ".join(CORE.split())


def test_a_host_passes_the_page_with_the_form(guide, model):
    model.script = [say("Registration costs 27.90 EUR.")]
    collect(guide, "pf1", message="what does it cost?", state={**start(guide, LOAN), "page": PAGE})
    assert "Registration costs 27.90 EUR." in _last(model) and "<form_context>" in _last(model)
    model.script = [say("ok")]
    collect(guide, "pf2", message="hi", state=start(guide, LOAN))
    assert "<page_facts" not in _last(model)                       # no page given: as before


def test_dushes_gives_the_form_agent_its_page(guide, model):
    site = Dushes(guide, SiteMap.load(SITE))
    here = next(p for p in site.site.pages if p.form and p.facts()["sections"])
    state = {"page": {"path": here.path}, "form": {**start(guide, LOAN), "form_id": here.form}}
    model.script = [say("Here is what the page says.")]

    async def go():
        return [e async for e in site.run("pf3", message="fill in my last name: Morozova", state=state)]
    asyncio.run(go())
    seen = " ".join(_text for call in model.calls for m in call
                    for _text in [m.content if isinstance(m.content, str) else str(m.content)])
    assert f'<page_facts page="{here.title}"' in seen and here.facts()["sections"][0]["text"][:30] in seen
