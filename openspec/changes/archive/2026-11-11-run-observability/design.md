# Design

## Context

Where the hooks go:
- **One run.** `FormGuide.run` wraps `_run`, which streams `graph.astream(inp, cfg, stream_mode=["custom", "updates"])` with `cfg = {"configurable": {"thread_id": ...}}` and maps stream writes to AG-UI events.
- **Model calls.** The `llm` node streams `model.astream(msgs)` and already logs `usage_metadata` per call: input, output, and `input_token_details.cache_read` for Anthropic.
- **Tool calls.** The `tools` node runs them one by one through `run_tool`.
- **Waiting for the user.** A card ends a run with an interrupt; the resume is a new run.
- **Debug endpoint.** `GET /debug/{thread_id}` exists under `debug=True` and returns the history.

The reasons for the change are in proposal.md.

## Goals / Non-Goals

**Goals:**
- Numbers that are cheap to collect: no extra model calls, under 1 ms of bookkeeping per turn.
- Work with whatever tracer a team already uses, without adding a dependency.
- Speed checks that run in the normal offline test suite.

**Non-Goals:**
- A metrics backend (Prometheus, OpenTelemetry metrics) or dashboards. The log line is structured, so a collector can pick it up; native exporters can come later.
- Measuring the browser's network time. The widget can compute it from `agui:run-start` and `run_stats` if a host wants it.

## Decisions

### A per-run collector passed through the stream writer

`stats.py` defines `RunStats`, with `start()`, `model_call(...)`, `tool_call(...)`, `first_token()` and `as_event()`.

`FormGuide.run` creates one per run and sets it in a context variable for the duration of the run. LangGraph runs the nodes in tasks that inherit that context, so `stats.current()` finds it there. It is not put into the graph config, because LangGraph copies `configurable` values into checkpoint metadata and an object would break the SQLite checkpointer. The interrupt ends the run, so time waiting for the user is never inside one.

Alternatives considered:
- A LangChain callback handler. Rejected as the primary path: it cannot see our tool loop (`run_tool` is ours, not LangChain tools) or the first answer text.
- Timing inside AG-UI mapping only. Rejected: it cannot split model time from tool time.

The checkpoint is unaffected: the collector lives in a context variable, not in the state or the config.

### First token = first visible answer text

Time to first token is taken when `_run` maps the first `text_delta`. Internal notes are not shown to the user and do not count. Per model call, `ttft_ms` is the first chunk of `astream`.

### Trace metadata through RunnableConfig

`cfg` gains:
- `run_name="formguide turn"`;
- `tags=["formguide", form_id, *config.tracing.tags]`;
- `metadata={thread_id, run_id, form_id, jsx_hash}`;
- `callbacks=[factory() for factory in tracing.callbacks]`.

LangGraph propagates all of these to every model and tool call, so LangSmith (enabled by its own environment variables) and any handler get the grouping for free. Factories are imported at config load time (`import_object`), so a typo fails early. Handlers are built once per `FormGuide` and reused; a factory may return a new handler per call if it wants.

### Emission and storage

`run_stats` is yielded right before the terminal event in every path: finished, interrupted and error. After yielding it, `run` logs the same dict to `formguide.stats` and appends it to `self._recent[thread_id]`, a `deque(maxlen=20)`. That buffer is in memory only, which is enough for a development endpoint. The transcript does not record stats: it is the user's view.

### Speed budgets

`tests/test_perf.py` uses `time.perf_counter()`. Each operation is run several times after one warm-up, and the minimum is compared to the budget, which keeps noise low. Budgets are set after measuring, at about 5 to 10 times the laptop number, and the failure message shows both numbers.

The widget's `test/perf.test.ts` uses `performance.now()` in happy-dom, with the same approach.

### Benchmark script

`scripts/bench.py` reuses the harness's HTTP/SSE client. It reads `run_stats` and needs no timing of its own. Scenarios are a small fixed list: a question, a fill with a card, a document question, a question card, a long form step. Each runs `--repeat N` times on fresh threads.

Cards are accepted automatically, as the harness does. Prices are a small table per model (input, output, cache-read per million tokens) and can be overridden with `--prices file.json`. Output: a table on stdout, and JSON in `backend/scripts/bench-<timestamp>.json`, which is gitignored like the logs.

### Demo display

`App.tsx` already listens to `agent_context` through `onEvent`; it also listens to `run_stats`. The "What the agent sees" panel then shows one line: "first token 1.2 s · total 4.8 s · model 3.9 s · tools 0.6 s · 3,104 in / 212 out · cache 87%".

## Risks / Trade-offs

- [Timing tests flake on slow CI] → minimum of several runs, generous budgets; the message shows both numbers.
- [Cache-read tokens differ by provider] → read `input_token_details.cache_read` when present, otherwise null; `cache_hit_rate` is null when unknown.
- [Tracer callbacks slow down every turn] → they are opt-in, and their cost shows up in `run_stats` totals, so the benchmark exposes it.
- [Stats leak data] → only numbers, tool names and ids; never message text or field values.

## Migration Plan

Additive. Clients that ignore unknown `CUSTOM` events are unaffected. Rollback: revert.
