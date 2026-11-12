---
title: 'Speed and tracing'
description: 'Turn timings, LangSmith and Langfuse, speed tests and the live benchmark.'
---

How to see where a turn's time goes, follow a conversation in a tracer, and catch slowdowns before users do.

| Question | Where to look |
|---|---|
| How long did this turn take, and why? | the `run_stats` event of the run (the demo shows it under "What the agent sees") |
| What did the model and the tools do, step by step? | a tracer: LangSmith, Langfuse or any LangChain callback handler |
| Did my change make things slower? | the offline speed tests (every `pytest` run) and the live benchmark |
| What happened in that user's last turns? | `GET /agent/debug/{thread_id}` (development) or the `formguide.stats` log lines |

Source: [`stats.py`](https://github.com/denvasylenko/dushes/blob/main/backend/formguide/stats.py), [`scripts/bench.py`](https://github.com/denvasylenko/dushes/blob/main/backend/scripts/bench.py), [`tests/test_perf.py`](https://github.com/denvasylenko/dushes/blob/main/backend/tests/test_perf.py), [`tests/test_observability.py`](https://github.com/denvasylenko/dushes/blob/main/backend/tests/test_observability.py).

---

## The numbers of every turn: `run_stats`

The last event of every run, right before `RUN_FINISHED` (or `RUN_ERROR`):

```json
{ "type": "CUSTOM", "name": "run_stats", "value": {
  "run_id": "…", "thread_id": "…",
  "ttft_ms": 1609,            // until the first word of the answer reached the stream
  "total_ms": 5585,           // the whole run; time waiting for the user on a card is never included
  "model_ms": 5012, "tool_ms": 41,
  "models": [ { "kind": "agent", "ms": 2310, "ttft_ms": 980, "input_tokens": 11205, "output_tokens": 96, "cache_read_tokens": 8120 }, … ],
  "tools":  [ { "name": "search_fields", "ms": 12, "error": false }, … ],
  "tokens": { "input": 23062, "output": 259, "cache_read": 16604 },
  "cache_hit_rate": 0.72
} }
```

| Number | Means | When it is high |
|---|---|---|
| `ttft_ms` | how long the user waits before text starts | the model thinks long before writing, or the first step is a tool call; a cold prompt cache |
| `total_ms` | the whole run | many tool rounds (see `tools`) |
| `model_ms` vs `tool_ms` | model time vs our tools (search, documents, extraction) | `tool_ms` high: the document researcher or reading an attachment |
| `models[].ttft_ms` | a model's own latency to the first chunk | provider load, a big prompt, high reasoning effort |
| `cache_hit_rate` | share of input tokens read from the prompt cache (cheaper and faster) | low on the first turn and after the cache expires (about 5 minutes without activity for Anthropic) |

Every run also writes the same numbers as one JSON line on the `formguide.stats` logger (INFO), ready for any log collector. The development endpoint `GET /agent/debug/{thread_id}` keeps the last 20 runs of each thread. Only numbers, tool names and ids are recorded, never message text or field values.

In a widget host: `chat.addEventListener('agui:event', e => e.detail.name === 'run_stats' && show(e.detail.value))`.

---

## Tracing

Every turn is a LangChain run named **"formguide turn"**:
- tags: `formguide`, the form id, and anything in `tracing.tags`;
- metadata: `thread_id`, `run_id`, `form_id`, `jsx_hash`.

These are inherited by every model call and tool call inside the turn, so a tracer can show one conversation as a list of turns, each with its steps.

**LangSmith** needs no code: set two environment variables before starting the server and every turn shows up there; filter by `metadata.thread_id` to follow one conversation.

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=...            # optional: LANGSMITH_PROJECT=formguide-demo
```

**Any other tracer** (Langfuse, Phoenix, your own): give a factory that returns a LangChain callback handler.

```yaml
tracing:
  callbacks: ["my_app.tracing:langfuse_handler"]   # def langfuse_handler(): return langfuse.langchain.CallbackHandler()
  tags: [staging]
```

`formguide check --config formguide.yaml` prints whether LangSmith is on and which callbacks are configured.

### OpenTelemetry: Azure Monitor, Zipkin, Jaeger, Datadog, any OTLP backend

`pip install 'formguide[otel]'` (add `otel-zipkin` or `otel-azure` for those exporters), then one key:

```yaml
tracing:
  otel:
    exporter: otlp                         # otlp | zipkin | azure_monitor | console | host | "module:factory"
    endpoint: "http://collector:4317"      # :4317 = gRPC, anything else = OTLP over HTTP
    headers: {api-key: "${OTLP_KEY}"}      # optional, for hosted collectors
    service_name: loan-assistant           # default: formguide
    sample_ratio: 1.0                      # 0..1; a sampled caller trace stays sampled
```

| Exporter | For | Notes |
| --- | --- | --- |
| `otlp` | an OpenTelemetry Collector, Jaeger, Grafana Tempo, Datadog, Honeycomb | gRPC on `:4317`, HTTP otherwise (`/v1/traces` is added) |
| `zipkin` | Zipkin | `endpoint: http://zipkin:9411/api/v2/spans`; needs `formguide[otel-zipkin]` |
| `azure_monitor` | Application Insights | the connection string in `endpoint` or `APPLICATIONINSIGHTS_CONNECTION_STRING`; needs `formguide[otel-azure]` |
| `console` | local debugging | prints spans to stdout |
| `host` | an app that already configured OpenTelemetry | formguide adds its spans to the app's tracer provider, nothing else |
| `"my_app.tracing:make_exporter"` | anything else | a factory returning any OTel `SpanExporter` |

What you get per turn (only ids, names, types and numbers: never message text or field values):

| Span | Attributes |
| --- | --- |
| `formguide.turn` | `formguide.thread_id`, `.run_id`, `.form_id`, `.stop` (`answer`, a card type, `frontend_tool`, `error`), `.total_ms`, `.ttft_ms`, `gen_ai.usage.input_tokens` / `output_tokens`; an event `formguide.card` (type, id) when the turn stops at a card |
| `formguide.model` | `formguide.model.role`, `gen_ai.request.model`, `formguide.ttft_ms`, `gen_ai.usage.*`, `formguide.usage.cache_read_tokens` |
| `formguide.tool` | `formguide.tool.name`; error status when the tool failed |

**Joining your app's trace.** A run request with a W3C `traceparent` (and `tracestate`) header makes the turn a child of that span, so one trace runs from your page or API through formguide to the model. In Python, pass `guide.run(..., trace_context={"traceparent": ...})`.

OpenTelemetry works next to LangSmith and `tracing.callbacks`; `run_stats` does not change.

---

## Speed tests (offline, every `pytest` run)

[`tests/test_perf.py`](https://github.com/denvasylenko/dushes/blob/main/backend/tests/test_perf.py) runs formguide's own work on the 221-field demo loan form, without a model, and fails when it gets much slower:

| Operation | Measured (laptop) | Budget |
|---|---|---|
| build one turn's context (outline + focus) | 0.8 ms | 10 ms |
| diff two configs | 0.9 ms | 10 ms |
| validate a 10-field card | < 1 ms | 10 ms |
| a whole turn through the graph with a 10-field card (scripted model) | 8 ms | 80 ms |

The widget has the same in [`test/perf.test.ts`](https://github.com/denvasylenko/dushes/blob/main/packages/agui-chat/test/perf.test.ts): 5,000 SSE events (4.6 ms, budget 60), one typewriter frame on a long answer (5.7 ms, budget 60), 200 messages (12 ms, budget 120). `PERF_PRINT=1 npx vitest run test/perf.test.ts` prints the numbers.

So formguide itself adds about 10 ms to a turn; the rest is the model and the tools you call.

---

## The live benchmark

[`scripts/bench.py`](https://github.com/denvasylenko/dushes/blob/main/backend/scripts/bench.py) plays five fixed scenarios against a running server, each on a fresh thread, accepting cards and picking the first option of questions like a user would, and reports the server's own `run_stats`:

```bash
cd backend
uv run python scripts/bench.py                          # the local demo
uv run python scripts/bench.py --repeat 3 --max-ttft 5 --max-turn 30   # fails (exit 1) above the thresholds
uv run python scripts/bench.py --base https://formguide-demo.fly.dev --password ...   # a hosted demo behind a password
uv run python scripts/bench.py --prices prices.json     # adds an estimated cost per turn
```

`prices.json` holds your model's prices per million tokens, e.g. `{"input": 5, "output": 25, "cache_read": 0.5}`. The results are also saved as `scripts/bench-<time>.json` to compare before and after a change.

**Baseline** (2026-11-11, the demo with Claude Opus 5.5 at low effort, one run each, warm server):

| Scenario | First token | Turn | Tool calls | Tokens in / out | Cache |
|---|---|---|---|---|---|
| question ("Where do I start?") | 3.4 s | 5.4 s | 1 | 14,815 / 216 | 37% |
| fill (name and birth date, card accepted) | 1.6 s | 5.6 s | 2 | 23,062 / 259 | 72% |
| choice (question card, then a field card) | 6.5 s | 11.9 s | 3 | 38,596 / 482 | 71% |
| documents (the car loan rate) | 2.2 s | 4.6 s | 0 | 7,354 / 298 | 75% |
| booking (service, barber, day and slot) | 4.0 s | 22.9 s | 10 | 75,526 / 888 | 65% |

What it tells us: the model's time dominates (formguide adds about 10 ms); a turn that walks a dependent chain (the booking: 10 tool calls in a row) is the slowest; the prompt cache saves about two thirds of the input tokens once a conversation is going. A long conversation that sat idle for a while starts cold (cache near 0%) and its first turn is noticeably slower.
