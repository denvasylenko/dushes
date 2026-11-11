"""Form core: layout, overlay, diff, dependencies, rendering. No models involved."""
from __future__ import annotations

import json

from demo.mock_forms import barber
from demo.mock_forms.loan_rules import compute_config
from demo.mock_forms.loan_spec import FORM_JSX
from formguide import ComponentMap
from formguide.domain.packs import DomainPack
from formguide.form.layout import LayoutIndex
from formguide.form.overlay import DepStore, Overlay, compute_diff
from formguide.form.render import locate, render_focus, render_outline

LOAN = DomainPack(form_id="loan_application", title="Loan", pii={"passport_number"})
LAY = LayoutIndex(FORM_JSX)


def test_layout_and_inherited_flags():
    assert not LAY.warnings
    ov = Overlay(LAY, compute_config(), LOAN.pii)
    assert LAY.nodes["passport_number"].addr == "1.1.2.2"
    assert ov["acc_business"].visible is False
    assert ov["business_ogrnip"].own_visible and not ov["business_ogrnip"].visible
    assert ov["loan_purpose"].disabled


def test_custom_component_library():
    jsx = '<Wizard name="w"><Step name="s1"><TextField name="a" /><Select name="b" /></Step></Wizard>'
    lay = LayoutIndex(jsx, ComponentMap(containers={"Wizard": "tabs", "Step": "tab"},
                                        fields={"TextField": "text", "Select": "select"}))
    assert not lay.warnings and lay.nodes["b"].role == "select" and lay.nodes["s1"].is_container


def test_diff_collapses_and_learns():
    deps = DepStore()
    st: dict = {}
    prev = Overlay(LAY, compute_config(st)).snapshot()
    st["loan_type"] = {"id": "mortgage", "name": "Mortgage"}
    ov = Overlay(LAY, compute_config(st))
    d = compute_diff(ov, prev)
    assert "tab_collateral" in d.appeared and "col_realty_type" not in d.appeared
    assert ("loan_purpose", 0, 4) in d.options and "loan_purpose" in d.enabled
    deps.observe(d, ov)
    assert "loan_type" in deps.drivers()
    assert "loan_type" in deps.hint(ov, "tab_collateral", "visible:on")


def test_dependency_needs_exact_observation():
    deps = DepStore()
    st: dict = {}
    prev = Overlay(LAY, compute_config(st)).snapshot()
    st.update(loan_type={"id": "auto", "name": "Car loan"}, employment_type={"id": "employee", "name": "Employed"})
    ov = Overlay(LAY, compute_config(st))
    deps.observe(compute_diff(ov, prev), ov)
    assert deps.hint(ov, "tab_collateral", "visible:on") == ""


def test_invalid_value_after_options_change():
    st = {"reg_region": {"id": "msk", "name": "Moscow"}, "reg_city": {"id": "zel", "name": "Zelenograd"}}
    prev = Overlay(LAY, compute_config(st)).snapshot()
    st["reg_region"] = {"id": "spb", "name": "Saint Petersburg"}
    assert "reg_city" in compute_diff(Overlay(LAY, compute_config(st)), prev).invalid_new


def test_pii_hidden_and_context_small():
    cfg = compute_config({"passport_number": "123456"})
    ov = Overlay(LAY, cfg, LOAN.pii)
    loc = locate(ov, {"activeTabs": {"main": "tab_applicant"}, "openAccordions": ["acc_passport"]})
    text = render_outline(ov, loc, DepStore(), LOAN, 1) + render_focus(ov, loc, DepStore())
    assert "123456" not in text and "<filled>" in text
    assert len(text) * 5 < len(json.dumps(cfg, ensure_ascii=False))


def test_steps_unlock_and_blockers():
    lay = LayoutIndex(barber.FORM_JSX)
    st: dict = {}
    ov = Overlay(lay, barber.compute_config(st))
    assert ov["visit_date"].disabled and ov["client_name"].disabled and ov["barber"].disabled
    st.update(service={"id": "kids", "name": "Kids haircut"})
    ov = Overlay(lay, barber.compute_config(st))
    assert [o["id"] for o in ov["barber"].options] == ["maria"] and ov["child_age"].visible
    ov = Overlay(LAY, compute_config({"loan_type": {"id": "mortgage", "name": "Mortgage"}}))
    assert ov.blockers("tab_collateral")[0].startswith('"Loan"')
