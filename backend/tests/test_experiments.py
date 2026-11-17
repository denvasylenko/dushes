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
