"""Repeated rows: a Repeat's template expands into rows; the agent fills, adds and removes them on a card."""
from __future__ import annotations

from types import SimpleNamespace

from formguide.form.layout import LayoutIndex
from formguide.form.overlay import Overlay
from formguide.form.render import render_container

from .conftest import say
from .test_agent import collect
from .test_questions import interrupt_value

JSX = ('<Form name="order"><Input name="customer"/><Repeat name="items"><Input name="product"/>'
       '<NumberInput name="qty"/></Repeat><Input name="address.city"/></Form>')
PROPS = {"order": {"label": "Order"}, "customer": {"label": "Customer"},
         "items": {"label": "Order lines", "min_rows": 1, "max_rows": 3},
         "product": {"label": "Product"}, "qty": {"label": "Quantity"}, "address.city": {"label": "City"}}


def config(**state):
    return {"props": PROPS, "state": state}


def test_rows_expand_from_the_config_and_the_hash_stays():
    lay = LayoutIndex(JSX)
    ov = Overlay(lay, config(**{"items.0.product": "Beans", "items.1.product": "Mug"}))
    assert [n for n in ov.layout.order if n.startswith("items.")] == [
        "items.0", "items.0.product", "items.0.qty", "items.1", "items.1.product", "items.1.qty"]
    assert ov["items.1.product"].value == "Mug" and ov["items.1.qty"].label == "Quantity"
    assert ov.layout.jsx_hash == lay.jsx_hash and lay.for_config(config()) is not ov.layout
    assert [n for n in Overlay(lay, config()).layout.order if n.startswith("items.")] == [
        "items.0", "items.0.product", "items.0.qty"]                       # min_rows 1: one empty row
    out = render_container(ov, "items", None)
    assert '[Row items.1] "Line 2"' in out and "items.1.product Input" in out


def test_a_dotted_name_is_a_row_only_for_a_declared_repeat():
    lay = LayoutIndex(JSX)
    assert lay.repeat_of("items.2.qty") == ("items", 2, "qty") and lay.repeat_of("address.city") is None
    assert Overlay(lay, config())["address.city"].label == "City"
    plain = LayoutIndex('<Form name="f"><Input name="a"/></Form>')
    assert plain.for_config(config()) is plain


def _form(guide):
    form = SimpleNamespace(jsx=JSX, form_id="order", domain=None)
    info = guide.register_form(form.jsx, form.form_id)
    return lambda **state: {"config": config(**state), "jsx_hash": info["jsx_hash"], "form_id": "order", "ui": {}}


def card(guide, model, thread, changes, state, caps=("ask", "rows")):
    model.script = [say("", ("c1", "propose_changes", {"changes": changes})), say("Ok.")]
    return interrupt_value(collect(guide, thread, message="do it", state=state, capabilities=list(caps)))


def test_fill_add_and_remove_rows_on_one_card(guide, model):
    st = _form(guide)(**{"items.0.product": "Beans", "items.0.qty": 1, "items.1.product": "Mug"})
    v = card(guide, model, "r1", [{"name": "items.1.qty", "value": 2},
                                  {"add_row": "items", "values": {"product": "Filters", "qty": 3}}], st)
    rows = {c["name"]: c for c in v["changes"]}
    assert rows["items.1.qty"]["value"] == 2
    add = rows["items.2"]
    assert add["op"] == "add_row" and add["index"] == 2 and add["values"]["product"] == "Filters"
    assert add["label"] == "New line 3"
    v = card(guide, model, "r2", [{"remove_row": "items", "index": 1}], st)
    assert v["changes"][0]["op"] == "remove_row" and v["changes"][0]["label"] == "Line 2"


def test_limits_conflicts_and_the_capability(guide, model):
    st = _form(guide)(**{"items.0.product": "Beans", "items.1.product": "Mug", "items.2.product": "Tea"})
    assert card(guide, model, "r3", [{"add_row": "items", "values": {"product": "X"}}], st) is None   # full (max 3)
    assert "the list is full" in str(model.calls[-1][-1].content)
    assert card(guide, model, "r4", [{"add_row": "items", "values": {}}], st, caps=("ask",)) is None
    assert "rows cannot be added or removed in this chat" in str(model.calls[-1][-1].content)
    assert card(guide, model, "r5", [{"remove_row": "items", "index": 1}, {"name": "items.1.qty", "value": 4}], st) is None
    assert "in a row this card removes" in str(model.calls[-1][-1].content)
