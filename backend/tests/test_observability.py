"""Turn timings (run_stats), the stats log line, the debug endpoint, and trace metadata for tracers."""
from __future__ import annotations

import json
import logging
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import tool

from demo.mock_forms import FORMS
from formguide.server import create_router

from .conftest import say
from .test_agent import collect, start
from .test_agui import check_order

LOAN = FORMS["loan_application"]


def stats_of(ev):
    return next(e["value"] for e in ev if e.get("name") == "run_stats")


def test_run_stats_come_last_with_models_and_tools(guide, model):
    model.script = [say("", ("t1", "search_fields", {"query": "phone"})), say("It is on the Applicant tab.")]
    ev = collect(guide, "o1", message="where is the phone?", state=start(guide, LOAN))
    check_order(ev)
    assert [e.get("name", e["type"]) for e in ev][-2:] == ["run_stats", "RUN_FINISHED"]
    s = stats_of(ev)
    assert s["thread_id"] == "o1" and s["run_id"] == ev[0]["runId"]
    assert len(s["models"]) == 2 and [t["name"] for t in s["tools"]] == ["search_fields"]
    assert s["ttft_ms"] is not None and s["total_ms"] >= s["ttft_ms"] >= 0
    assert s["tools"][0]["error"] is False and s["model_ms"] >= 0


def test_run_stats_on_errors_and_failed_tools(guide, model):
    model.script = [say("", ("t1", "get_field", {"name": "no_such_field"})), RuntimeError("provider is down")]
    ev = collect(guide, "o2", message="hi", state=start(guide, LOAN))
    check_order(ev)
    assert [e.get("name", e["type"]) for e in ev][-2:] == ["run_stats", "RUN_ERROR"]
    s = stats_of(ev)
    assert s["tools"][0]["error"] is True and s["ttft_ms"] is None


def test_waiting_for_the_user_is_not_counted(guide, model):
    model.script = [say("", ("t1", "propose_changes", {"changes": [{"name": "first_name", "value": "Anna"}]}))]
    state = start(guide, LOAN)
    first = stats_of(collect(guide, "o3", message="I am Anna", state=state))
    time.sleep(0.3)                                   # the user thinks
    model.script = [say("Done.")]
    second = stats_of(collect(guide, "o3", resume={"accepted": True, "config": state["config"]}))
    assert second["total_ms"] < 300 and len(second["models"]) == 1
    assert first["run_id"] != second["run_id"]


def test_stats_log_line_and_debug_endpoint(guide, model, caplog):
    caplog.set_level(logging.INFO, logger="formguide.stats")
    model.script = [say("Hello!")]
    collect(guide, "o4", message="hi", state=start(guide, LOAN))
    line = json.loads(next(r.message for r in caplog.records if r.name == "formguide.stats"))
    assert line["thread_id"] == "o4" and "total_ms" in line
    app = FastAPI()
    app.include_router(create_router(guide, debug=True), prefix="/agent")
    runs = TestClient(app).get("/agent/debug/o4").json()["runs"]
    assert len(runs) == 1 and runs[0]["run_id"] == line["run_id"]
    plain = FastAPI()
    plain.include_router(create_router(guide, debug=False), prefix="/agent")
    assert TestClient(plain).get("/agent/debug/o4").status_code == 404


class Capture(BaseCallbackHandler):
    def __init__(self):
        self.chains, self.tools = [], []

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, tags=None, metadata=None, **kw):
        if parent_run_id is None:
            self.chains.append({"name": kw.get("name"), "tags": tags or [], "metadata": metadata or {}})

    def on_tool_start(self, serialized, input_str, *, metadata=None, **kw):
        self.tools.append(metadata or {})


def test_trace_metadata_and_callbacks(guide, model):
    cap = Capture()
    guide._callbacks = [cap]
    guide.config.tracing.tags = ["staging"]

    @tool
    def lookup_branch(city: str) -> str:
        """Find the nearest branch."""
        return "Main street 1"

    guide._tools.append(lookup_branch)
    model.script = [say("", ("t1", "lookup_branch", {"city": "Lyon"})), say("Main street 1.")]
    collect(guide, "o5", message="nearest branch?", state=start(guide, LOAN))
    root = cap.chains[0]
    assert root["name"] == "formguide turn"
    assert {"formguide", "loan_application", "staging"} <= set(root["tags"])
    assert root["metadata"]["thread_id"] == "o5" and root["metadata"]["form_id"] == "loan_application"
    assert cap.tools and cap.tools[0].get("thread_id") == "o5"     # metadata reaches every call inside


def test_tracing_yaml(tmp_path):
    import pytest

    from formguide.config import load_config

    f = tmp_path / "formguide.yaml"
    f.write_text('model: {class: "tests.conftest:ScriptedChatModel"}\n'
                 'tracing: {callbacks: ["tests.test_observability:Capture"], tags: [demo]}\n')
    cfg = load_config(f)
    assert cfg.tracing.callbacks == [Capture] and cfg.tracing.tags == ["demo"]
    f.write_text('model: {class: "tests.conftest:ScriptedChatModel"}\ntracing: {callbacks: ["nope.module:handler"]}\n')
    with pytest.raises(ValueError, match="nope.module:handler"):
        load_config(f)
