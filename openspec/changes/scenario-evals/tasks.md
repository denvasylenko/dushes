# Tasks

## 1. Scenarios and runner

- [x] 1.1 Move the HTTP session logic of `chat_harness.py` into a shared module; `chat_harness.py` keeps working (run one scenario against the demo server)
- [x] 1.2 Define and validate the scenario format; add 8 scenarios covering Dushes answers, navigation, hand-off, a form fill, an attachment, a foreign question on a form page, an invented-fact trap and a Russian conversation; verify unknown keys are rejected in a test
- [x] 1.3 Implement the simulated user over the shared session; verify with `--offline` in a pytest smoke test

## 2. Judge and report

- [x] 2.1 Implement the deterministic checks and the judge with the rubric and caps; verify the capping rule in a unit test
- [x] 2.2 Write the JSON report, the summary, the baseline and the exit codes; verify a regression exit in a test with a fake baseline
- [x] 2.3 Document in `backend/observability.mdx` and `reference/cli.md`; add the eval command to CLAUDE.md's check list for agent changes; build passes

## 3. Checks

- [x] 3.1 Run all scenarios live once against the demo server and save the first baseline; `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd site && npm run build` pass
