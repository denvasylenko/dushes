# Design

## Context

`chat_harness.py` already drives the demo server like the frontend (config, ui, cards, form backend edits) with keyword checks. The live benchmark (`bench.py`) measures speed. Neither judges quality.

## Goals / Non-Goals

**Goals:** a repeatable quality score per scenario; cheap to add a scenario; usable before every agent change.

**Non-Goals:** no CI run with real models by default (keys and cost); no human labelling tool.

## Decisions

- **Real HTTP, not in-process.** The scenarios exercise routing, hand-off and cards exactly as a page does; the client logic moves out of `chat_harness.py` into a shared module both use.
- **Deterministic checks first, the judge second.** String and event checks cap the score, so a judge's leniency cannot hide a hard failure.
- **Models from `models:`.** The user and judge use configured roles (`eval_user`, `eval_judge`, falling back to the agent model), so any provider works.
- **Baseline file** `backend/evals/baseline.json`, updated with `--save-baseline` only on purpose.

## Risks / Trade-offs

- [Judge noise] → a fixed rubric, temperature 0, reasons required per point, and the margin for regressions.
- [Cost] → scenario selection by name and a `--repeat` default of 1.
