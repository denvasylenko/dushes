"""Speed budgets for formguide's own work on the 221-field demo loan form (no model calls).

Each operation runs several times after a warm-up and the fastest run is compared with its budget.
Budgets are about ten times the numbers measured on a laptop (Apple M-series, Python 3.13):
context 0.8 ms, diff 0.9 ms, a whole scripted turn with a 10-field card 8 ms. They catch a regression
that makes something many times slower, not noise.
"""
from __future__ import annotations

import asyncio
import time

from demo.mock_forms import FORMS
from formguide.agent.tools import ToolCtx, _t_propose_changes
from formguide.domain.packs import DomainPack
from formguide.form.layout import LayoutIndex
from formguide.form.overlay import DepStore, Overlay, compute_diff
from formguide.form.render import locate, render_focus, render_outline

from .conftest import say

LOAN = FORMS["loan_application"]
BUDGET_MS = {"context": 10, "diff": 10, "card": 10, "turn": 80}


def fastest_ms(fn, runs: int = 15) -> float:
    fn()
    best = float("inf")
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best * 1000


def within(name: str, ms: float) -> None:
    assert ms <= BUDGET_MS[name], f"{name}: {ms:.1f} ms, budget {BUDGET_MS[name]} ms"


LAYOUT = LayoutIndex(LOAN.jsx)
CONFIG = LOAN.compute(None)
PACK = DomainPack(form_id=LOAN.form_id)
TEXT_FIELDS = [n.name for n in LAYOUT.fields() if n.role == "text" and Overlay(LAYOUT, CONFIG)[n.name].editable][:10]


def test_the_form_is_the_big_one():
    assert sum(1 for _ in LAYOUT.fields()) >= 200 and len(TEXT_FIELDS) == 10


def test_context_building_budget():
    deps = DepStore(None)

    def build():
        ov = Overlay(LAYOUT, CONFIG)
        loc = locate(ov, {})
        render_outline(ov, loc, deps, PACK, 1)
        render_focus(ov, loc, deps, PACK)

    within("context", fastest_ms(build))


def test_diff_budget():
    snap = Overlay(LAYOUT, CONFIG).snapshot()
    after = LOAN.compute({**CONFIG["state"], "loan_type": {"id": "auto", "name": "Car loan"}})
    within("diff", fastest_ms(lambda: compute_diff(Overlay(LAYOUT, after), snap)))


def test_card_validation_budget():
    changes = [{"name": n, "value": "Anna"} for n in TEXT_FIELDS]

    def validate():
        ctx = ToolCtx(ov=Overlay(LAYOUT, CONFIG), deps=DepStore(None), pack=PACK, loc=None)  # type: ignore[arg-type]
        _t_propose_changes({"changes": changes}, ctx)
        assert len(ctx.pending_changes) == 10

    within("card", fastest_ms(validate))


def test_whole_scripted_turn_budget(guide, model):
    h = guide.register_form(LOAN.jsx, LOAN.form_id, LOAN.domain)["jsx_hash"]
    state = {"config": CONFIG, "jsx_hash": h, "form_id": LOAN.form_id}
    n = [0]

    def turn():
        n[0] += 1
        model.script = [say("", ("t1", "propose_changes", {"changes": [{"name": f, "value": "x"} for f in TEXT_FIELDS]}))]

        async def go():
            return [e async for e in guide.run(f"perf{n[0]}", message="go", state=state)]

        ev = asyncio.run(go())
        assert any(e.get("name") == "on_interrupt" for e in ev)

    within("turn", fastest_ms(turn, runs=8))
