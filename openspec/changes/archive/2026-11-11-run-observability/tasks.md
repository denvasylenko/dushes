# Tasks

## 1. Collecting the numbers

- [x] 1.1 `formguide/stats.py`: `RunStats` (model calls, tool calls, first token, totals, cache hit rate, `as_event()`).
- [x] 1.2 `agent/graph.py`:
  - `llm` records duration, time to first chunk and tokens per call (through `stats.current()`);
  - `tools` records each tool's duration and error;
  - `confirm` records the held tool it runs.
- [x] 1.3 `guide.py`:
  - create the collector per run and set it in a context variable for the run;
  - mark the first answer text;
  - yield `run_stats` before the terminal event in every path;
  - log one JSON line on `formguide.stats`;
  - keep the last 20 per thread.

## 2. Tracing

- [x] 2.1 `guide.py`: `run_name`, tags and metadata in the run config; callbacks from `tracing`.
- [x] 2.2 `config.py`: `tracing: {callbacks, tags}` in code and YAML; factories imported at load, an unknown one fails with its name.
- [x] 2.3 `server.py`: `GET /debug/{thread_id}` returns `runs`. `cli.py check` prints the tracing status (LangSmith environment, callbacks).

## 3. Speed tests and benchmark

- [x] 3.1 `tests/test_perf.py`: budgets for context building, diff, a 10-field card and a whole scripted turn on the loan form; budgets set from measured numbers.
- [x] 3.2 Tests for `run_stats` (event order, a card excluded, tools and models listed, the log line, the debug endpoint), trace metadata (a capturing callback) and the YAML tracing key.
- [x] 3.3 `packages/agui-chat/test/perf.test.ts`: 200 messages, a typewriter frame, 5,000 SSE events.
- [x] 3.4 `backend/scripts/bench.py`: scenarios, `--repeat`, `--max-ttft`, `--max-turn`, `--prices`, the table and JSON output. Gitignore its JSON files. Run it once against the demo server and record the baseline in the docs.

## 4. Demo and docs

- [x] 4.1 `frontend/src/App.tsx`: show the run stats line in the "What the agent sees" panel. The harness prints stats per turn.
- [x] 4.2 New `docs/observability.md`: what each number means, LangSmith and Langfuse setup, the debug endpoint, the speed tests, the benchmark and its baseline.
- [x] 4.3 Update `docs/configuration.md` (`tracing`), `docs/architecture.md`, README (testing and benchmark commands), `docs/ui-components.md` (the event list) and `docs/architecture-pages.html` (Configuration and Integrate). Build the site, then republish the artifact.
- [x] 4.4 Run `openspec validate --all --strict`, `python3 scripts/check_english.py`, the backend tests and the widget tests.

## Workflow follow-up

- Archive the change with `/opsx:archive` after it is implemented and verified.
