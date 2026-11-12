# Tasks

## 1. Setup and config

- [x] 1.1 `tracing.otel` in `TracingConfig` and `load_config` (exporter, endpoint, headers, service_name, sample_ratio; unknown keys refused; a clear error when the SDK is missing)
- [x] 1.2 `formguide/otel.py`: provider, sampler, resource, lazy exporters (otlp gRPC / HTTP, zipkin, azure_monitor, console, host, `module:factory`)
- [x] 1.3 Extras `otel`, `otel-zipkin`, `otel-azure` in `pyproject.toml` (versions checked on PyPI); flush on app shutdown

## 2. Spans

- [x] 2.1 `formguide.turn` around each run in `guide.run`, with thread / run / form ids and the stop reason
- [x] 2.2 `formguide.model` and `formguide.tool` children from the RunStats hooks (start times, tokens with GenAI attribute names, error status)
- [x] 2.3 `formguide.card` event on interrupts
- [x] 2.4 No content in spans: attributes built only from ids, names and numbers

## 3. Propagation

- [x] 3.1 `POST /run` extracts `traceparent` / `tracestate`; `guide.run(trace_context=...)`
- [x] 3.2 Widget option `traceparent` sent as `forwardedProps.traceparent` with each run (the server uses it when the headers are absent)

## 4. Tests

- [x] 4.1 In-memory exporter: span tree of a turn with a card, attributes, the stop reason
- [x] 4.2 No message text or field values in any attribute or event
- [x] 4.3 A `traceparent` header becomes the parent; without OTel the header is ignored
- [x] 4.4 Config errors: unknown key, missing SDK, bad factory; LangSmith and callbacks unchanged; run_stats unchanged

## 5. Docs and wrap-up

- [x] 5.1 `site/`: backend/observability (OpenTelemetry: Azure Monitor, Zipkin, OTLP collector, custom exporter, host provider), reference/configuration, reference/http-api, widget option, concepts/architecture
- [x] 5.2 `openspec validate --all --strict`, `check_english.py`, backend and widget tests, `cd site && npm run build`
