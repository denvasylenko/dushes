"""Experimental features behind an activation code (the owner, 2026-11-17: "make this option available in + with
activation code of experimental feature"): on a gated host the decision model runs only for a request that carries
a pass, and a visitor without one sends nothing to the chooser and sees no label or trace."""
import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from formguide import experiments

CODE = "open-sesame-42"


@pytest.fixture(autouse=True)
def _ungated():
    yield
    experiments.uninstall()


def _app():
    exp = experiments.Experiments({"anna": CODE}, "s" * 32, (experiments.DECISION_MODEL,))
    app = FastAPI()
    experiments.install(app, exp)
    app.include_router(experiments.create_experiments_router(exp), prefix="/experiments")

    @app.post("/run")
    async def run():
        async def body():
            yield f"allowed={experiments.allowed()}"   # asked while the answer streams, as the layer does
        return StreamingResponse(body())

    return app


def test_a_host_without_a_gate_is_not_gated():
    assert experiments.allowed() is True
    assert experiments.Experiments.from_env().enabled is False


def test_only_a_request_with_a_pass_is_allowed():
    client = TestClient(_app())
    assert client.post("/run").text == "allowed=False"
    assert client.get("/experiments").json() == {"features": ["decision_model"], "unlocked": False}
    assert client.post("/experiments/unlock", json={"code": "wrong-code-000"}).status_code == 403
    got = client.post("/experiments/unlock", json={"code": CODE}).json()
    assert got["person"] == "anna" and got["features"] == ["decision_model"]
    head = {"X-Experiment-Pass": got["pass"]}
    assert client.post("/run", headers=head).text == "allowed=True"
    assert client.get("/experiments", headers=head).json()["unlocked"] is True
    # a pass that was changed, and the next request without one
    assert client.post("/run", headers={"X-Experiment-Pass": got["pass"][:-1] + "0"}).text in ("allowed=False",)
    assert client.post("/run").text == "allowed=False"


def test_codes_are_a_separate_list(monkeypatch):
    monkeypatch.setenv("EXPERIMENT_CODES", "anna=short")
    with pytest.raises(ValueError, match="EXPERIMENT_CODES"):
        experiments.Experiments.from_env()
    monkeypatch.setenv("EXPERIMENT_CODES", f"anna={CODE}")
    monkeypatch.delenv("INTENT_PROVIDER", raising=False)
    exp = experiments.Experiments.from_env()
    assert exp.enabled and exp.features == ()             # no chooser on this host: nothing to open
    monkeypatch.setenv("INTENT_PROVIDER", "jev")
    assert experiments.Experiments.from_env().features == ("decision_model",)


def test_one_entry_field_opens_what_the_code_is_listed_for():
    """The owner (2026-11-17): "has to be two in one under one option in menu": one code entry, two switches. The
    code is tried against the voice list too; a person only on the voice list gets no pass for the decision model."""
    from formguide import voice
    exp = experiments.Experiments({"anna": CODE}, "s" * 32, (experiments.DECISION_MODEL,))
    talk = voice.Gate(experiments._Codes({"anna": CODE, "ben": "voice-only-77"}, "v" * 32))
    exp.join("voice", talk)
    app = FastAPI()
    app.include_router(experiments.create_experiments_router(exp), prefix="/experiments")
    client = TestClient(app)
    assert client.get("/experiments").json()["features"] == ["decision_model", "voice"]
    both = client.post("/experiments/unlock", json={"code": CODE}).json()
    assert both["features"] == ["decision_model", "voice"] and both["pass"] == both["passes"]["decision_model"]
    assert talk.person(both["passes"]["voice"]) == "anna" and exp.gate.person(both["pass"]) == "anna"
    only = client.post("/experiments/unlock", json={"code": "voice-only-77"}).json()
    assert only["features"] == ["voice"] and only["pass"] == "" and talk.person(only["passes"]["voice"]) == "ben"
    assert client.post("/experiments/unlock", json={"code": "nobody-here-00"}).status_code == 403
