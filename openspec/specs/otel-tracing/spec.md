# otel-tracing Specification

## Purpose
OpenTelemetry export of formguide's own spans: how it is configured, which exporters it supports, what each span carries (ids, names and numbers, never content), and how a turn joins the caller's trace.

## Requirements

### Requirement: OpenTelemetry configuration
The config SHALL accept `tracing.otel: {exporter, endpoint?, headers?, service_name?, sample_ratio?}`. `exporter` SHALL be one of `otlp`, `zipkin`, `azure_monitor`, `console`, `host`, or an import string of a factory that returns an OpenTelemetry `SpanExporter`. With `host`, formguide SHALL use the process's existing tracer provider and configure no exporter. A missing OpenTelemetry package SHALL fail config loading with the extra to install.

#### Scenario: Zipkin
- **WHEN** the config has `tracing: {otel: {exporter: zipkin, endpoint: "http://zipkin:9411/api/v2/spans"}}`
- **THEN** every turn is exported to Zipkin as a trace

#### Scenario: A custom exporter
- **WHEN** `exporter` is `"my_app.tracing:make_exporter"`
- **THEN** formguide exports its spans through the exporter that factory returns

#### Scenario: Not installed
- **WHEN** `tracing.otel` is set and the OpenTelemetry SDK is not installed
- **THEN** loading the config fails with a message naming `formguide[otel]`

### Requirement: Turn spans
Each run SHALL produce a span `formguide.turn` with attributes `formguide.thread_id`, `formguide.run_id`, `formguide.form_id` and `formguide.stop` (answer, a card type, frontend_tool or error). An interrupt SHALL add an event `formguide.card` with the card type and id.

#### Scenario: A turn that waits on a question
- **WHEN** a turn ends with an ask_user card
- **THEN** its `formguide.turn` span has `formguide.stop` ask and a `formguide.card` event of type ask

### Requirement: Model and tool spans
Each model call SHALL be a child span `formguide.model` with the model role, the model name, latency, time to first token and token counts; each tool call a child span `formguide.tool` with the tool name and an error status when it failed.

#### Scenario: A turn that ends with a card
- **WHEN** a turn calls get_fields, then propose_changes, and waits for the user
- **THEN** the trace has one `formguide.turn` span with two `formguide.tool` children, the model spans, a `formguide.card` event of type set_fields, and `formguide.stop` set_fields

### Requirement: No content in spans
Span names, attributes and events SHALL carry only ids, names, types and numbers, never message text, field values or document content.

#### Scenario: A field value
- **WHEN** a turn proposes a passport number
- **THEN** no span attribute or event contains that number

### Requirement: Continuing the host's trace
When a run carries a W3C `traceparent` (and `tracestate`), as HTTP headers, in `forwardedProps`, or as `trace_context` in Python, the turn span SHALL be a child of that context; without them the turn SHALL start a new trace.

#### Scenario: A request from a traced page
- **WHEN** `POST /run` arrives with a `traceparent` header
- **THEN** the `formguide.turn` span has that trace id and the header's span as its parent
