# Proposal

## Why

Keyword checks in `backend/scripts/chat_harness.py` catch crashes but not bad answers: the wrong agent answering, an invented fact, a missing card. The cabinet session's runs with a simulated owner and a judge model found almost every real failure; formguide needs the same for Dushes and the forms, run on every change and scored so a regression shows as a number.

## What Changes

- Scenario files (`backend/evals/*.yaml`): a persona, a goal, the starting page or form, what the user knows, the number of turns, and the expectations (facts that must or must not appear, the agent that should answer, cards that should be shown, a page that should be reached).
- A runner (`uv run python scripts/evals.py [names] [--model ...]`): a simulated-user model plays the persona through the real HTTP API, like the frontend (answers cards, follows directives), then a judge model scores the transcript 0 to 10 against the expectations and a fixed rubric, with a reason per point lost.
- A report: per-scenario scores and reasons in `scripts/runs/evals-<time>.json` and a summary table; a run fails when a scenario falls below its `min_score` or the average drops by more than a set margin from the last saved baseline.
- An offline smoke mode with a scripted model, so `pytest` checks that the runner and the scenario files work without API keys.

## Capabilities

### New Capabilities
- `scenario-evals`: scenario files, the simulated user, the judge's scoring and the report with regression limits.

### Modified Capabilities
(none)

## Impact

- New: `backend/evals/` (scenarios), `backend/scripts/evals.py`, a smoke test in `backend/tests/`.
- Reuses the HTTP client logic of `chat_harness.py` (moved into a shared module).
- Docs: `backend/observability.mdx` (a section on evals), `reference/cli.md`; CLAUDE.md's check list gains the eval command for agent changes.
