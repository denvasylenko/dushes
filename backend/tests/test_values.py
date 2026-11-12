"""Component value formats: field specs, reading values leniently, writing them in the form's own format."""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from formguide import FormGuide, GuideConfig, Models
from formguide.form.layout import ComponentMap, FieldSpec
from formguide.form.overlay import Overlay
from formguide.form.values import read_options
from formguide.server import create_router

from .conftest import say
from .test_agent import collect

JSX = """
<Form name="main">
  <Select name="loan_type" />
  <RadioGroup name="contact_time" />
  <MultiSelect name="channels" />
  <Toggle name="consent" />
  <Calendar name="birth_date" />
  <Amount name="amount" />
  <AmountText name="income" />
  <Phone name="phone" />
  <Broken name="broken_phone" />
</Form>
"""

COMPONENTS = ComponentMap(fields={
    "Select": {"role": "select", "value": "id", "options_prop": "items"},
    "RadioGroup": {"role": "radio", "value": "name"},
    "MultiSelect": {"role": "multiselect", "value": "ids"},
    "Toggle": {"role": "bool", "true": "Y", "false": "N"},
    "Calendar": {"role": "date", "format": "%d.%m.%Y"},
    "Amount": "number",
    "AmountText": {"role": "number", "value": "string"},
    "Phone": {"role": "text", "codec": "tests.test_values:PhoneCodec"},
    "Broken": {"role": "text", "codec": "tests.test_values:BrokenCodec"},
})


class PhoneCodec:
    def decode(self, raw, props):
        return raw["country"] + raw["number"]

    def encode(self, value, props):
        return {"country": value[:2], "number": value[2:]}


class BrokenCodec:
    def encode(self, value, props):
        raise RuntimeError("no way")


def config(**state):
    props = {
        "main": {"visible": True},
        "loan_type": {"label": "Loan type", "items": [{"value": "auto", "label": "Car loan", "group": "secured"},
                                                       {"value": "cash", "label": "Cash loan"}]},
        "contact_time": {"label": "Contact time", "options": ["Morning", "Evening"]},
        "channels": {"label": "Channels", "options": {"sms": "SMS", "email": "Email", "post": "Post"}},
        "consent": {"label": "Consent"},
        "birth_date": {"label": "Birth date"},
        "amount": {"label": "Amount"},
        "income": {"label": "Income"},
        "phone": {"label": "Phone"},
        "broken_phone": {"label": "Other phone"},
    }
    base = {"loan_type": None, "contact_time": None, "channels": [], "consent": "N", "birth_date": None,
            "amount": None, "income": None, "phone": None, "broken_phone": None}
    return {"props": props, "state": {**base, **state}}


@pytest.fixture
def g(tmp_path, model):
    return FormGuide(GuideConfig(models=Models(agent=model), data_dir=tmp_path, components=COMPONENTS))


def state_of(g, **values):
    h = g.register_form(JSX, "custom")["jsx_hash"]
    return {"config": config(**values), "jsx_hash": h, "form_id": "custom"}


def card(g, model, thread, changes, **values):
    model.script = [say("", ("t1", "propose_changes", {"changes": changes}))]
    ev = collect(g, thread, message="go", state=state_of(g, **values))
    found = [e for e in ev if e.get("name") == "on_interrupt"]
    tool = model.calls and [m for m in model.calls[-1]]
    return (json.loads(found[0]["value"]) if found else None), tool


def test_reading_values_in_the_forms_own_format(g):
    st = state_of(g, loan_type="auto", contact_time="Evening", channels=["sms", "post"], consent="N",
                  birth_date="31.05.1990", amount="250 000", phone={"country": "+7", "number": "9001234567"})
    ov = Overlay(g.layout(st["jsx_hash"]), st["config"])
    assert ov["loan_type"].value == {"id": "auto", "name": "Car loan"} and ov["loan_type"].filled
    assert not ov["loan_type"].invalid_value
    assert ov["contact_time"].value == {"id": "Evening", "name": "Evening"}
    assert [c["id"] for c in ov["channels"].value] == ["sms", "post"] and ov["channels"].filled
    assert ov["consent"].value is False and not ov["consent"].filled
    assert ov["birth_date"].value == "1990-05-31"
    assert ov["amount"].value == 250000
    assert ov["phone"].value == "+79001234567"
    assert '"Car loan" (id=auto)' in ov.display_value(ov["loan_type"])


def test_unreadable_and_out_of_options_values(g):
    st = state_of(g, birth_date="tomorrow", loan_type="mortgage", channels="sms, fax")
    ov = Overlay(g.layout(st["jsx_hash"]), st["config"])
    assert ov["birth_date"].unreadable and ov["birth_date"].filled
    assert "unreadable" in ov.display_value(ov["birth_date"])
    assert ov["loan_type"].invalid_value and ov["channels"].invalid_value


def test_card_values_are_written_in_the_forms_format(g, model):
    value, _ = card(g, model, "v1", [
        {"name": "loan_type", "value": "Car loan"},
        {"name": "contact_time", "value": "evening"},
        {"name": "channels", "value": ["SMS", "email"]},
        {"name": "consent", "value": "yes"},
        {"name": "birth_date", "value": "1991-02-03"},
        {"name": "amount", "value": "250 000"},
        {"name": "income", "value": 1200.0},
        {"name": "phone", "value": "+79001234567"},
    ])
    by = {c["name"]: c for c in value["changes"]}
    assert by["loan_type"]["value"] == "auto" and by["loan_type"]["display"] == "Car loan"
    assert by["contact_time"]["value"] == "Evening"
    assert by["channels"]["value"] == ["sms", "email"] and by["channels"]["display"] == "SMS, Email"
    assert by["consent"]["value"] == "Y" and by["consent"]["display"] == "✓"
    assert by["birth_date"]["value"] == "03.02.1991"
    assert by["amount"]["value"] == 250000 and by["amount"]["display"] == "250000"
    assert by["income"]["value"] == "1200"
    assert by["phone"]["value"] == {"country": "+7", "number": "9001234567"}


def test_option_objects_are_written_back_as_given(tmp_path, model):
    comps = ComponentMap(fields={"Select": {"role": "select", "options_prop": "items"}})
    g = FormGuide(GuideConfig(models=Models(agent=model), data_dir=tmp_path, components=comps))
    h = g.register_form('<Form name="main"><Select name="loan_type" /></Form>', "x")["jsx_hash"]
    cfg = {"props": {"main": {}, "loan_type": config()["props"]["loan_type"]}, "state": {"loan_type": None}}
    model.script = [say("", ("t1", "propose_changes", {"changes": [{"name": "loan_type", "value": "auto"}]}))]
    ev = collect(g, "v2", message="go", state={"config": cfg, "jsx_hash": h, "form_id": "x"})
    v = json.loads(next(e for e in ev if e.get("name") == "on_interrupt")["value"])
    assert v["changes"][0]["value"] == {"value": "auto", "label": "Car loan", "group": "secured"}


def test_invalid_multiselect_item_and_failing_codec_are_refused(g, model):
    value, sent = card(g, model, "v3", [{"name": "channels", "value": ["SMS", "fax"]},
                                        {"name": "broken_phone", "value": "+71234"}])
    assert value is None                                       # nothing passed, so no card
    text = " ".join(str(m.content) for m in sent)
    assert "fax" in text and "sms:SMS" in text and "codec could not write" in text


def test_prefill_uses_the_forms_format(g):
    st = state_of(g)
    res = asyncio.run(g.suggest_prefill(st, data={"loan_type": "Cash loan", "consent": True, "amount": "1 000"}))
    by = {v["name"]: v for v in res["values"]}
    assert by["loan_type"]["value"] == "cash" and by["loan_type"]["display"] == "Cash loan"
    assert by["consent"]["value"] == "Y"
    assert by["amount"]["value"] == 1000


def test_option_keys_detection():
    sel = FieldSpec(role="select")
    for opts, first in [([{"value": "m", "label": "Male"}], ("m", "Male")),
                        ([{"key": "m", "label": "Male"}], ("m", "Male")),
                        ([{"code": "m", "title": "Male"}], ("m", "Male")),
                        (["Male", "Female"], ("Male", "Male")),
                        ({"m": "Male"}, ("m", "Male"))]:
        got, warn = read_options(sel, {"options": opts})
        assert (got[0]["id"], got[0]["name"]) == first and warn is None
    got, warn = read_options(sel, {"options": [{"uid": 1, "caption": "A"}]})
    assert warn and "option_keys" in warn
    got, warn = read_options(FieldSpec(role="select", option_keys=("uid", "caption")),
                             {"options": [{"uid": 1, "caption": "A"}]})
    assert got[0]["id"] == 1 and warn is None


def test_field_spec_errors_and_yaml(tmp_path):
    from formguide.config import load_config

    with pytest.raises(ValueError, match="optons_prop"):
        ComponentMap(fields={"Select": {"role": "select", "optons_prop": "items"}})
    with pytest.raises(ValueError, match="unknown role"):
        ComponentMap(fields={"Select": "dropdown"})
    with pytest.raises(ValueError, match="not valid for role"):
        ComponentMap(fields={"Select": {"role": "select", "value": "ids"}})
    f = tmp_path / "formguide.yaml"
    f.write_text("model: {class: \"tests.conftest:ScriptedChatModel\"}\n"
                 "components:\n  fields:\n    Toggle: {role: bool, true: Y, false: N}\n"
                 "    Select: {role: select, value: id, option_keys: {id: code, name: title}}\n")
    cfg = load_config(f)
    assert cfg.components.spec("Toggle").true == "Y" and cfg.components.spec("Toggle").false == "N"
    assert cfg.components.spec("Select").option_keys == ("code", "title")
    assert cfg.components.spec("Dropdown") is None             # a fields map replaces the default one


def test_value_warnings_on_registration(g):
    app = FastAPI()
    app.include_router(create_router(g), prefix="/agent")
    c = TestClient(app)
    cfg = config(loan_type="mortgage", birth_date="tomorrow")
    cfg["props"]["contact_time"] = {"label": "Contact time", "options": [{"uid": 1, "caption": "Morning"}]}
    del cfg["props"]["channels"]["options"]
    w = c.post("/agent/layouts", json={"jsx": JSX, "form_id": "custom", "config": cfg}).json()["warnings"]
    text = "\n".join(w)
    assert "loan_type <Select>: the value" in text and "value: id" in text
    assert "birth_date <Calendar>: cannot read" in text and "format" in text
    assert "contact_time <RadioGroup>" in text and "option_keys" in text
    assert "channels <MultiSelect>: no props.options" in text
    assert c.post("/agent/layouts", json={"jsx": JSX, "form_id": "custom",
                                          "config": config(loan_type="auto")}).json()["warnings"] == []


def test_cli_checks_a_form(tmp_path, capsys):
    from formguide.cli import main

    (tmp_path / "formguide.yaml").write_text(
        "model: {class: \"tests.conftest:ScriptedChatModel\"}\n"
        "components:\n  fields:\n    Select: {role: select, value: id, options_prop: items}\n")
    (tmp_path / "form.jsx").write_text('<Form name="main"><Select name="loan_type" /></Form>')
    good = {"props": {"loan_type": {"items": [{"value": "auto", "label": "Car loan"}]}}, "state": {"loan_type": "auto"}}
    (tmp_path / "ok.json").write_text(json.dumps(good))
    good["state"]["loan_type"] = "boat"
    (tmp_path / "bad.json").write_text(json.dumps(good))
    args = ["check", "--config", str(tmp_path / "formguide.yaml"), "--jsx", str(tmp_path / "form.jsx")]
    assert main(args + ["--form-config", str(tmp_path / "ok.json")]) == 0
    out = capsys.readouterr().out
    assert "<Select> select value=id options_prop=items" in out and out.strip().endswith("OK")
    assert main(args + ["--form-config", str(tmp_path / "bad.json")]) == 1
    assert "matches no option" in capsys.readouterr().out


def test_default_tags_for_radio_and_multiselect():
    from formguide.form.layout import LayoutIndex
    lay = LayoutIndex('<Form name="f"><RadioGroup name="gender"/><MultiSelect name="channels"/></Form>')
    assert lay.nodes["gender"].role == "radio" and lay.nodes["channels"].role == "multiselect"
    assert not [w for w in lay.warnings if "unknown" in w.lower()]
