# Design

## Context

- `stats.py` already records every model call (`model_call(started, first_chunk, usage, kind)`) and tool call (`tool_call(name, started, error)`) into a `RunStats` held in a context variable for the run (`activate` / `deactivate` in `guide.run`).
- `guide._run` builds the LangChain run config (run name, tags, metadata, callbacks), so LangChain tracers already see each turn.
- A run ends at a card, so time waiting for the user is never inside a run.

## Goals / Non-Goals

**Goals:** first-class OTel spans with formguide's own semantics; any exporter, including a custom one; joining the host's trace; zero cost when off.

**Non-Goals:**
- metrics and logs over OTel (a later change, using the same provider);
- instrumenting LangChain internals (prompt templates, retries); a host can still add an instrumentor next to ours;
- spans for the docs assistant.

## Decisions

1. **Spans come from the RunStats hooks, not from a LangChain callback.**
   - The turn span opens in `guide.run` where `RunStats` is activated; `model_call` / `tool_call` close child spans with explicit start times (`start_time` from the recorded `perf_counter`, mapped to the wall clock at run start).
   - Why: the hooks already exist and carry the formguide meaning (role, card, stop reason). A callback handler would see LangChain's view (chains, prompts) and need filtering.
   - Alternative: an OpenInference-style callback. Rejected as the primary path; hosts can add one.
2. **`formguide/otel.py` owns the provider.**
   - `setup(cfg)` builds a `TracerProvider` with `Resource(service.name = service_name or "formguide")`, a `BatchSpanProcessor` around the chosen exporter and a parent-based `TraceIdRatioBased` sampler from `sample_ratio` (a sampled caller trace stays sampled).
   - Exporters are imported lazily: `otlp` → `opentelemetry-exporter-otlp`, gRPC for `:4317`, otherwise HTTP; `zipkin` → `opentelemetry-exporter-zipkin-json`; `azure_monitor` → `azure-monitor-opentelemetry-exporter`, connection string from `endpoint` or `APPLICATIONINSIGHTS_CONNECTION_STRING`; `console` → the SDK's `ConsoleSpanExporter`.
   - `host` uses `trace.get_tracer_provider()` and adds nothing.
   - When OTel is off, a no-op tracer is used and the hooks cost one attribute check.
3. **Propagation.**
   - `server.py` extracts `traceparent` / `tracestate` with the W3C `TraceContextTextMapPropagator` and passes the context to `guide.run(trace_context=...)`. Python callers pass the same keyword.
   - The widget gets an optional `traceparent: () => string` option, sent as `forwardedProps.traceparent` (the plugin cannot set request headers); the server uses it when the headers are absent.
4. **Attributes** use a `formguide.` prefix, plus the GenAI semantic conventions where they fit: `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`. Azure and Datadog then show token counts natively. Values are ids, names and numbers only, enforced by building attributes from RunStats fields, never from messages.
5. **Extras:**
   - `otel = ["opentelemetry-sdk>=1.40", "opentelemetry-exporter-otlp>=1.40"]`;
   - `otel-zipkin = ["formguide[otel]", "opentelemetry-exporter-zipkin-json>=1.40"]`;
   - `otel-azure = ["formguide[otel]", "azure-monitor-opentelemetry-exporter>=1.0.0b50"]`.
   - Checked on PyPI at implementation: SDK 1.45.2, Azure exporter 1.0.0b59.

## Risks / Trade-offs

- **Clock mapping.** `perf_counter` → wall time is mapped once per run, which is accurate enough for traces (sub-millisecond drift).
- **BatchSpanProcessor on shutdown.** The FastAPI app's shutdown hook calls `provider.shutdown()` so the last spans flush.
- **Async context.** The turn span is set as current inside `guide.run`, and tool spans are children through the run's context variable, not through OTel's implicit context, so concurrent runs do not mix.
