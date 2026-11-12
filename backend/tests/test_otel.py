"""OpenTelemetry: turn / model / tool spans, the card event, trace propagation, no content in spans."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from formguide import FormGuide
from formguide.config import load_config
from formguide.otel import check
from formguide.server import create_router

from .conftest import say
from .test_agent import collect, start
from .test_questions import LOAN

EXPORTER = InMemorySpanExporter()
TP = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"


def make_exporter():
    return EXPORTER


@pytest.fixture
def traced(guide, model):
    global EXPORTER
    EXPORTER = InMemorySpanExporter()   # a shut-down exporter drops spans: one per test
    guide.config.tracing.otel = {"exporter": "tests.test_otel:make_exporter", "service_name": "formguide-test"}
    g = FormGuide(guide.config)
    yield g, model
    g.otel.provider.shutdown()


def spans(g):
    g.otel.provider.force_flush()
    return EXPORTER.get_finished_spans()


def test_a_turn_that_ends_with_a_card(traced):
    g, model = traced
    model.script = [say("", ("t1", "get_fields", {"container": "acc_passport"})),
                    say("", ("t2", "propose_changes", {"changes": [{"name": "passport_number", "value": "4510123456"}]}))]
    collect(g, "o1", message="my passport is 4510 123456", state=start(g, LOAN))
    got = spans(g)
    turn = next(s for s in got if s.name == "formguide.turn")
    kids = [s for s in got if s.parent and s.parent.span_id == turn.context.span_id]
    assert turn.attributes["formguide.thread_id"] == "o1" and turn.attributes["formguide.form_id"] == "loan_application"
    assert turn.attributes["formguide.stop"] == "set_fields"
    assert [e.name for e in turn.events] == ["formguide.card"] and turn.events[0].attributes["formguide.card.type"] == "set_fields"
    assert sorted(s.attributes.get("formguide.tool.name") for s in kids if s.name == "formguide.tool") == [
        "get_fields", "propose_changes"]
    assert any(s.name == "formguide.model" and s.attributes["formguide.model.role"] == "agent" for s in kids)
    assert turn.resource.attributes["service.name"] == "formguide-test"
    # no content: neither the message nor the value appears anywhere
    blob = repr([(s.attributes, [e.attributes for e in s.events]) for s in got])
    assert "4510" not in blob and "passport is" not in blob


def test_an_answer_and_a_failed_tool(traced):
    g, model = traced
    model.script = [say("", ("t1", "get_field", {"name": "nope"})), say("Here you go.")]
    collect(g, "o2", message="hi", state=start(g, LOAN))
    got = spans(g)
    turn = next(s for s in got if s.name == "formguide.turn")
    tool = next(s for s in got if s.name == "formguide.tool")
    assert turn.attributes["formguide.stop"] == "answer" and tool.status.status_code.name == "ERROR"


def test_the_callers_trace_is_continued(traced):
    g, model = traced
    model.script = [say("Hi.")]
    app = FastAPI()
    app.include_router(create_router(g), prefix="/agent")
    st = start(g, LOAN)
    body = {"threadId": "o3", "runId": "r1", "messages": [{"role": "user", "content": "hi"}], "state": st,
            "tools": [], "context": [], "forwardedProps": {}}
    TestClient(app).post("/agent/run", json=body, headers={"traceparent": TP})
    turn = next(s for s in spans(g) if s.name == "formguide.turn")
    assert format(turn.context.trace_id, "032x") == "0af7651916cd43dd8448eb211c80319c"
    assert format(turn.parent.span_id, "016x") == "b7ad6b7169203331"

    EXPORTER.clear()
    model.script = [say("Hi.")]
    collect(g, "o4", message="hi", state=st, trace_context={"traceparent": TP})
    turn = next(s for s in spans(g) if s.name == "formguide.turn")
    assert format(turn.context.trace_id, "032x") == "0af7651916cd43dd8448eb211c80319c"


def test_without_otel_the_header_changes_nothing(guide, model):
    assert guide.otel is None
    model.script = [say("Hi.")]
    ev = collect(guide, "o5", message="hi", state=start(guide, LOAN), trace_context={"traceparent": TP})
    assert ev[-1]["type"] == "RUN_FINISHED"


def test_config_checks(tmp_path):
    with pytest.raises(ValueError, match="unknown key"):
        check({"exporter": "otlp", "port": 1})
    with pytest.raises(ValueError, match="exporter must be"):
        check({"exporter": "jaeger"})
    with pytest.raises(ValueError, match="sample_ratio"):
        check({"sample_ratio": 2})
    assert check({})["exporter"] == "otlp"
    p = tmp_path / "formguide.yaml"
    p.write_text("model: anthropic:claude-haiku-5-5\ntracing: {otel: {exporter: console, service_name: forms}}\n")
    assert load_config(p).tracing.otel == {"exporter": "console", "service_name": "forms"}


def test_exporters_and_run_stats_unchanged(traced):
    from formguide.otel import _exporter

    assert type(_exporter({"exporter": "otlp", "endpoint": "http://collector:4318"})).__module__.endswith("http.trace_exporter")
    assert type(_exporter({"exporter": "otlp", "endpoint": "http://collector:4317"})).__module__.endswith("grpc.trace_exporter")
    assert type(_exporter({"exporter": "console"})).__name__ == "ConsoleSpanExporter"
    with pytest.raises(ValueError, match="otel-zipkin"):
        _exporter({"exporter": "zipkin"})
    with pytest.raises(ValueError, match="otel-azure"):
        _exporter({"exporter": "azure_monitor", "endpoint": "InstrumentationKey=x"})
    g, model = traced
    model.script = [say("Hi.")]
    ev = collect(g, "o6", message="hi", state=start(g, LOAN))
    stats = [e for e in ev if e.get("name") == "run_stats"]
    assert stats and set(stats[0]["value"]) >= {"run_id", "total_ms", "models", "tools", "tokens"}
