## ADDED Requirements

### Requirement: OpenTelemetry next to LangChain tracers
OpenTelemetry export (see the otel-tracing capability) SHALL work together with LangSmith and `tracing.callbacks`: enabling one SHALL NOT disable or change the others, and `run_stats` SHALL stay unchanged.

#### Scenario: LangSmith and Azure Monitor at once
- **WHEN** LangSmith is enabled through its environment variables and `tracing.otel.exporter` is `azure_monitor`
- **THEN** each turn appears in both, and the run_stats event is the same as without them
