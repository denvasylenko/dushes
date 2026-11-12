# Proposal

## Why

Tracing today reaches LangSmith (environment variables) and any LangChain callback handler (Langfuse, Phoenix, custom). Enterprises standardise on OpenTelemetry: Azure Monitor / Application Insights, Zipkin, Jaeger, Grafana Tempo, Datadog and Honeycomb all take OTel. A host can wire a third-party LangChain instrumentor itself, but those spans know nothing about formguide's turns, cards and conversations, and they do not join the host's own request trace.

## What Changes

- **`tracing.otel`** in the config: `{exporter, endpoint?, headers?, service_name?, sample_ratio?}`.
  - `exporter` is `otlp` (gRPC or HTTP by the endpoint), `zipkin`, `azure_monitor`, `console`, or an import string `"module:factory"` returning any OTel `SpanExporter`, so a custom backend needs no formguide change.
  - Hosts that already configure an OTel `TracerProvider` can set `exporter: host`: formguide only adds its spans to the host's provider.
- **formguide's own spans.**
  - `formguide.turn` covers one run, with `thread_id`, `run_id`, `form_id`, the stop reason (answer, card type, frontend tool, error) and totals.
  - Children: `formguide.model` (model role, model name, latency, time to first token, input / output / cache tokens) and `formguide.tool` (tool name, latency, error).
  - A `formguide.card` event marks an interrupt, with the card type and id. The wait for the user is not counted: the next run is a new span, linked to the previous one by the thread.
  - Only ids, names and numbers go into spans; never message text or field values, the same rule as `run_stats`.
- **Continuing the host's trace.** When `POST /run` carries W3C `traceparent` / `tracestate` headers, the turn span becomes their child. The widget's `traceparent` option sends the page's context as `forwardedProps.traceparent`, used when the headers are absent.
- **Optional dependency** `formguide[otel]`, with exporter extras `otel-zipkin` and `otel-azure`. Without them, `tracing.otel` fails at config load with the install hint. Everything works next to LangSmith and `tracing.callbacks`.

## Capabilities

### New Capabilities
- `otel-tracing`: OpenTelemetry export: the config, exporters, span names and attributes, trace propagation, privacy of attributes.

### Modified Capabilities
- `run-observability`: the tracers requirement now names OpenTelemetry as a third way next to LangSmith and callbacks.
- `http-api`: `POST /run` reads `traceparent` / `tracestate`.

## Impact

- Backend: new `formguide/otel.py`; `stats.py` (one span per recorded model and tool call); `guide.py` (turn span around the run); `server.py` (context from the headers); `config.py` (`tracing.otel`); `pyproject.toml` (extras). Tests with the OTel in-memory exporter.
- Widget: optional `traceparent` option (a function), sent as a header with each run.
- Docs: `site/` backend/observability (OpenTelemetry section with Azure, Zipkin, OTLP and custom examples), reference/configuration, reference/http-api, concepts/architecture.
