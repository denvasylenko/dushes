"""OpenTelemetry tracing: formguide's own spans, exported anywhere OTel goes.

    tracing:
      otel: {exporter: otlp, endpoint: "http://collector:4317"}      # or zipkin, azure_monitor, console,
                                                                      # host, "my_app.tracing:make_exporter"

Spans (only ids, names, types and numbers: never message text or field values):
- `formguide.turn`: one run; `formguide.thread_id`, `.run_id`, `.form_id`, `.stop` (answer, a card type,
  frontend_tool, error); an event `formguide.card` when the run stops at a card;
- `formguide.model`: a model call (role, model, latency, time to first token, `gen_ai.usage.*` tokens);
- `formguide.tool`: a tool call (name, latency, error status).
A run request's W3C `traceparent` / `tracestate` make the turn a child of the caller's trace.

Needs `pip install 'formguide[otel]'` (plus `otel-zipkin` or `otel-azure` for those exporters).
"""
from __future__ import annotations

import atexit
import os
import time
from typing import Any

from .skills import import_object

KEYS = {"exporter", "endpoint", "headers", "service_name", "sample_ratio"}
BUILTIN = ("otlp", "zipkin", "azure_monitor", "console", "host")


def check(spec: Any) -> dict:
    """Validate `tracing.otel` (raises ValueError with what to fix)."""
    if not isinstance(spec, dict):
        raise ValueError("tracing.otel must be a mapping, e.g. {exporter: otlp, endpoint: http://collector:4317}")
    unknown = set(spec) - KEYS
    if unknown:
        raise ValueError(f"tracing.otel: unknown key(s) {sorted(unknown)}; allowed: {sorted(KEYS)}")
    exp = spec.get("exporter") or "otlp"
    if not isinstance(exp, str) or (exp not in BUILTIN and ":" not in exp):
        raise ValueError(f"tracing.otel.exporter must be one of {', '.join(BUILTIN)} or 'module:factory'")
    ratio = spec.get("sample_ratio", 1.0)
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1:
        raise ValueError("tracing.otel.sample_ratio must be a number from 0 to 1")
    if spec.get("headers") is not None and not isinstance(spec["headers"], dict):
        raise ValueError("tracing.otel.headers must be a mapping")
    try:
        import opentelemetry.sdk.trace  # noqa: F401
    except ImportError:
        raise ValueError("tracing.otel needs OpenTelemetry: pip install 'formguide[otel]'") from None
    return {**spec, "exporter": exp}


def _exporter(spec: dict) -> Any:
    exp, endpoint, headers = spec["exporter"], spec.get("endpoint"), spec.get("headers") or None
    try:
        if exp == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            return ConsoleSpanExporter()
        if exp == "otlp":
            if endpoint and (endpoint.rstrip("/").endswith(":4317") or endpoint.startswith("grpc")):
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as Grpc
                return Grpc(endpoint=endpoint, headers=headers)
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as Http
            url = endpoint and (endpoint if endpoint.rstrip("/").endswith("/v1/traces")
                                else endpoint.rstrip("/") + "/v1/traces")
            return Http(endpoint=url, headers=headers) if url else Http(headers=headers)
        if exp == "zipkin":
            try:
                from opentelemetry.exporter.zipkin.json import ZipkinExporter
            except ImportError:
                raise ValueError("the zipkin exporter needs: pip install 'formguide[otel-zipkin]'") from None
            return ZipkinExporter(endpoint=endpoint) if endpoint else ZipkinExporter()
        if exp == "azure_monitor":
            try:
                from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            except ImportError:
                raise ValueError("the azure_monitor exporter needs: pip install 'formguide[otel-azure]'") from None
            conn = endpoint or os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
            if not conn:
                raise ValueError("azure_monitor needs a connection string: tracing.otel.endpoint or "
                                 "APPLICATIONINSIGHTS_CONNECTION_STRING")
            return AzureMonitorTraceExporter(connection_string=conn)
    except ImportError as e:
        raise ValueError(f"tracing.otel ({exp}): {e}; pip install 'formguide[otel]'") from None
    factory = import_object(exp)
    return factory()


class Tracer:
    """formguide's OTel tracer; `None` from `setup()` means tracing is off."""

    def __init__(self, spec: dict):
        from opentelemetry import trace
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        self._trace = trace
        self._prop = TraceContextTextMapPropagator()
        if spec["exporter"] == "host":   # the application already configured OpenTelemetry
            provider = trace.get_tracer_provider()
        else:
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

            provider = TracerProvider(
                resource=Resource.create({"service.name": spec.get("service_name") or "formguide"}),
                sampler=ParentBasedTraceIdRatio(float(spec.get("sample_ratio", 1.0))))
            provider.add_span_processor(BatchSpanProcessor(_exporter(spec)))
            atexit.register(provider.shutdown)   # flush the last spans
        self.provider = provider
        self.tracer = provider.get_tracer("formguide")

    def turn(self, *, thread_id: str, run_id: str, form_id: str, carrier: dict | None) -> TurnSpan:
        ctx = self._prop.extract(carrier) if carrier else None
        span = self.tracer.start_span("formguide.turn", context=ctx, attributes={
            "formguide.thread_id": thread_id, "formguide.run_id": run_id, "formguide.form_id": form_id or ""})
        return TurnSpan(self, span)


class TurnSpan:
    """The span of one run; child spans get explicit times from the run's stats."""

    def __init__(self, tracer: Tracer, span: Any):
        self._t = tracer
        self.span = span
        self._wall0 = time.time_ns()
        self._perf0 = time.perf_counter()

    def _ns(self, perf: float) -> int:
        return self._wall0 + int((perf - self._perf0) * 1e9)

    def child(self, name: str, started: float, attrs: dict[str, Any], error: bool = False) -> None:
        ctx = self._t._trace.set_span_in_context(self.span)
        s = self._t.tracer.start_span(name, context=ctx, start_time=self._ns(started),
                                      attributes={k: v for k, v in attrs.items() if v is not None})
        if error:
            from opentelemetry.trace import Status, StatusCode
            s.set_status(Status(StatusCode.ERROR))
        s.end(end_time=time.time_ns())

    def card(self, kind: str, card_id: str) -> None:
        self.span.add_event("formguide.card", {"formguide.card.type": kind, "formguide.card.id": card_id})

    def end(self, stop: str, totals: dict[str, Any]) -> None:
        self.span.set_attribute("formguide.stop", stop)
        for k, v in totals.items():
            if v is not None:
                self.span.set_attribute(k, v)
        if stop == "error":
            from opentelemetry.trace import Status, StatusCode
            self.span.set_status(Status(StatusCode.ERROR))
        self.span.end()


def setup(spec: dict | None) -> Tracer | None:
    return Tracer(check(spec)) if spec else None
