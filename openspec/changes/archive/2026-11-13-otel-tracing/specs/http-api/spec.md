## ADDED Requirements

### Requirement: Trace context on run requests
`POST /run` SHALL read the W3C `traceparent` and `tracestate` headers (or, without them, `forwardedProps.traceparent` / `tracestate`, which the widget sends) and pass them to the run, so the turn joins the caller's trace when OpenTelemetry is configured. The headers SHALL be ignored otherwise.

#### Scenario: Headers without OpenTelemetry
- **WHEN** a run request carries `traceparent` and `tracing.otel` is not set
- **THEN** the run behaves exactly as without the header
