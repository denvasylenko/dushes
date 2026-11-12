"""Ask AI: one reader-sized answer out of the model's cards, and typo-tolerant search."""
from docs_ai.agent import asked_stack, compose


def blk(bid, lang, code, page="/backend/configuration/", section="Build it up"):
    return {"id": bid, "lang": lang, "label": lang, "code": code, "url": f"https://d.x{page}#s", "page": page,
            "section": section}


def test_code_cards_merge_into_one_without_repeats():
    a = {"kind": "code", "caption": "Domain pack sources", "blocks": [blk("b1", "yaml", "domain_packs: {dir: domain_packs}"),
                                                                    blk("b2", "python", "DomainPackRegistry(directory=...)")]}
    b = {"kind": "code", "caption": "Point the backend", "blocks": [blk("b3", "yaml", "domain_packs:  {dir: domain_packs}")]}
    c = {"kind": "code", "caption": "Minimal", "blocks": [blk("b4", "yaml", "model: x", section="Other topic")]}
    pages = {"kind": "pages", "pages": [{"url": "https://d.x/backend/configuration/", "title": "Configuration"},
                                        {"url": "https://d.x/frontend/react-hook-form/", "title": "react-hook-form"},
                                        {"url": "https://d.x/backend/domain-packs/", "title": "Domain packs"},
                                        {"url": "https://d.x/backend/models/", "title": "Models"}]}
    out = compose([a, pages, b, c], "where do domain packs come from")
    assert [x["kind"] for x in out] == ["code", "pages"]
    assert [x["id"] for x in out[0]["blocks"]] == ["b1", "b2"]   # b3 is the same code, b4 another topic
    assert [p["title"] for p in out[1]["pages"]] == ["react-hook-form", "Domain packs"]   # its own page dropped, at most 2


def test_the_asked_stack_comes_first():
    web = {"kind": "code", "caption": "A schema", "blocks": [blk("w1", "tsx", "useFormguide(form, schema)", section="S")]}
    py = {"kind": "code", "caption": "Python", "blocks": [blk("p1", "python", "FormGuide(GuideConfig())", section="S"),
                                                         blk("p2", "yaml", "model: x", section="S")]}
    out = compose([web, py], "how to configure my pthon?")
    assert asked_stack("how to configure my pthon?") == "server"
    assert out[0]["caption"] == "Python" and [b["lang"] for b in out[0]["blocks"]][:2] == ["python", "yaml"]
    assert asked_stack("set it up in React") == "web" and asked_stack("what is a card") == ""


def test_steps_win_over_repeated_code_and_cards_are_capped():
    steps = {"kind": "steps", "title": "Set up", "steps": [{"text": "Add", "block": blk("b1", "yaml", "a: 1")}]}
    code = {"kind": "code", "caption": "", "blocks": [blk("b1", "yaml", "a: 1")]}
    live = {"kind": "live", "specimen": "chips", "about": "x"}
    out = compose([code, steps, live, dict(live), {"kind": "pages", "pages": [{"url": "https://d.x/z/", "title": "Z"}]}])
    assert [x["kind"] for x in out] == ["steps", "live", "pages"]   # the code repeated the step's block


def test_search_forgives_a_typo():
    from formguide.knowledge.index import BM25Index, Chunk

    from docs_ai.corpus import NS, Corpus

    idx = BM25Index()
    idx.add([Chunk("p1#0", NS, "p1", "Python", "Configure", "Configure the python backend with uvicorn."),
             Chunk("p2#0", NS, "p2", "React", "Schema", "A schema for useFormguide in react.")])
    c = Corpus(index=idx, pages=2, sections=2, source="test")
    assert "pytho" in c.correct("configure my pthon")
    assert c.search("pthon backend", k=1)[0].doc_id == "p1"
