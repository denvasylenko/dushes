# Proposal

## Why

There is no way to see where a turn's time goes or to tell whether a change made the agent slower. Today:
- the graph logs token usage per model call, but nothing measures time;
- traces carry no conversation metadata, so LangSmith or another tracer shows a pile of unrelated runs;
- the tests check behaviour, never speed.

Before showing the demo to others, and before every prompt, model or widget change, we need three things: per-turn numbers, traces grouped by conversation, and speed budgets that fail when something gets slow.

## What Changes

- **Turn timings.** Each run measures:
  - time to first token;
  - total time, excluding the time a card waits for the user;
  - every model call: duration, input, output and cached tokens, time to first token;
  - every tool call: duration and whether it failed.

  The numbers are sent as `CUSTOM run_stats` before the run ends, written as one structured log line per run (`formguide.stats`), and kept for the thread's recent runs under `GET /debug/{thread_id}`.
- **Tracing.** Every graph run carries:
  - `run_name` "formguide turn";
  - tags: form id, `interrupt_mode`;
  - metadata: thread_id, run_id, form_id, jsx_hash.

  LangSmith therefore groups a conversation's runs as soon as its environment variables are set, and so does any LangChain tracer. A new `tracing` setting adds callback handlers (`"module:factory"`, e.g. Langfuse) and extra tags. `formguide check` reports whether tracing is on.
- **Speed tests (offline, no model).** A `perf` test module with budgets on our own overhead for the 221-field loan form:
  - building the per-turn context;
  - the diff;
  - validating a 10-field card;
  - a whole scripted turn through the graph.

  The widget gets matching budgets: rendering 200 messages, the typewriter frame cost, SSE parsing of 5,000 events. Budgets sit well above today's numbers, to catch regressions rather than noise.
- **Live benchmark.** `backend/scripts/bench.py` runs a fixed set of scenarios against a running server and reports, per scenario and as medians or p90:
  - time to first token, turn time, tool calls, tokens and cache hit rate;
  - an approximate cost from a configurable price table.

  It saves JSON and exits non-zero when `--max-ttft` / `--max-turn` thresholds are exceeded.
- **Demo.** The "What the agent sees" panel gets a timings line (first token, total, model and tool time, tokens, cache). The widget's `agui:event` already carries `run_stats`, so any host can show it.

Not breaking: a new `CUSTOM` event and a new optional config key.

## Capabilities

### New Capabilities
- `run-observability`: turn timings (the event, the log line, the debug endpoint), trace metadata and tracer callbacks, offline speed budgets, and the live benchmark.

### Modified Capabilities
- `agui-protocol`: "Progress and suggestion events" also lists `run_stats`.
- `http-api`: the development-only `GET /debug/{thread_id}` returns recent run stats as well.

## Impact

- Backend:
  - new `formguide/stats.py`, which collects timings and tokens;
  - `agent/graph.py`: hooks in `llm` and `tools`, excluding the wait on a card;
  - `guide.py`: run config with name, tags and metadata, emitting `run_stats`, the log line, the recent-runs buffer;
  - `config.py`: the `tracing` key;
  - `server.py`: the debug endpoint;
  - `cli.py`: the check output;
  - new `tests/test_perf.py`;
  - new `scripts/bench.py`;
  - the harness prints run stats.
- Widget: `test/perf.test.ts`; types for `run_stats`. The demo's "What the agent sees" panel shows the timings.
- Docs:
  - a new `docs/observability.md` (reading the numbers, LangSmith and Langfuse setup, the benchmark);
  - `configuration.md`, `architecture.md`, README, the architecture pages.
- No new runtime dependency. LangSmith and Langfuse are the user's choice and are imported only when configured.
