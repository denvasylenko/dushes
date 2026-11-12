"""Ask AI's answer recipes: loaded from files, one picked per question, added to the instructions."""
from pathlib import Path

from docs_ai import recipes


def test_the_shipped_recipes_load():
    names = {r.name for r in recipes.load()}
    assert {"configure-backend", "connect-frontend", "card-look", "how-it-works", "can-it", "troubleshoot"} <= names
    assert all(r.body and r.when for r in recipes.load())


def test_a_recipe_per_kind_of_question():
    rs = recipes.load()
    pick = lambda q: (recipes.pick(rs, q) or recipes.Recipe("none", "", "")).name  # noqa: E731
    assert pick("how to configure my pthon?") == "configure-backend"
    assert pick("how do I add the chat to my React page") == "connect-frontend"
    assert pick("what does the slider card look like") == "card-look"
    assert pick("can it read a passport photo?") == "can-it"
    assert pick("I get a 401 error on attachments") == "troubleshoot"
    assert pick("explain how a turn works") == "how-it-works"
    assert pick("hello") == "none"


def test_own_recipes_from_a_folder(tmp_path: Path):
    (tmp_path / "pricing.md").write_text("---\nname: pricing\ntitle: Pricing\nwhen: [price, cost]\n---\nSay it is free.\n")
    rs = recipes.load(tmp_path)
    r = recipes.pick(rs, "what does it cost")
    assert r and r.name == "pricing"
    assert recipes.instructions(r) == "\n\nHow to answer this question (Pricing):\nSay it is free."
    assert recipes.instructions(None) == ""


def test_the_recipe_reaches_the_model(tmp_path):
    from .test_docs_ai import _ask, _client

    client, model = _client(tmp_path)
    with client as c:
        _ask(c, "how to configure my pthon backend")
    assert "How to answer this question (Configure the backend)" in model.calls[0][0].content
