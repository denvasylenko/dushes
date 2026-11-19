"""Turn timings: where a run's time and tokens go.

One RunStats per run, set for the run in a context variable (so it reaches the graph's nodes and never
enters a checkpoint); nodes record into it with `current()`. A run ends at a card (an interrupt), so
time waiting for the user is never counted.
The result goes out as CUSTOM `run_stats`, one JSON log line on `formguide.stats`, and the debug
endpoint's recent runs. Only numbers, names and ids: never message text or field values.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any

_current: ContextVar["RunStats | None"] = ContextVar("formguide_run_stats", default=None)


def model_id(model: object) -> str | None:
    """A chat model's id ("claude-haiku-5-5"), read from the usual attributes of LangChain models, or None."""
    for attr in ("model", "model_name", "model_id"):
        v = getattr(model, attr, None)
        if isinstance(v, str) and v:
            return v
    return None


class RunStats:
    def __init__(self, run_id: str, thread_id: str):
        self.run_id = run_id
        self.thread_id = thread_id
        self.t0 = time.perf_counter()
        self.ttft: float | None = None
        self.models: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []
        self.choice: str | None = None  # the run's model choice (models.choices), when the server has choices
        self.agent: str | None = None   # "site" for Dushes' own calls; the UI agent leaves it out
        self.span: Any = None   # the run's OpenTelemetry turn span (otel.TurnSpan), when tracing is on

    @staticmethod
    def now() -> float:
        return time.perf_counter()

    def _ms(self, since: float) -> int:
        return round((time.perf_counter() - since) * 1000)

    def first_token(self) -> None:
        if self.ttft is None:
            self.ttft = time.perf_counter() - self.t0

    def model_call(self, started: float, first_chunk: float | None, usage: dict | None, kind: str = "agent",
                   model: str | None = None) -> None:
        u = usage or {}
        details = u.get("input_token_details") or {}
        if self.span is not None:
            self.span.child("formguide.model", started, {
                "formguide.model.role": kind, "gen_ai.request.model": model,
                "formguide.ttft_ms": round((first_chunk - started) * 1000) if first_chunk else None,
                "gen_ai.usage.input_tokens": u.get("input_tokens"), "gen_ai.usage.output_tokens": u.get("output_tokens"),
                "formguide.usage.cache_read_tokens": details.get("cache_read")})
        self.models.append({
            "kind": "code" if model == "code" else kind, "model": None if model == "code" else model, "at_ms": round((started - self.t0) * 1000), "ms": self._ms(started),
            "ttft_ms": round((first_chunk - started) * 1000) if first_chunk else None,
            "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
            "cache_read_tokens": details.get("cache_read"),
            "cache_write_tokens": details.get("cache_creation"),
        })

    def tool_call(self, name: str, started: float, error: bool = False) -> None:
        if self.span is not None:
            self.span.child("formguide.tool", started, {"formguide.tool.name": name}, error=bool(error))
        self.tools.append({"name": name, "at_ms": round((started - self.t0) * 1000), "ms": self._ms(started),
                           "error": bool(error)})

    def as_event(self) -> dict[str, Any]:
        def total(key: str) -> int | None:
            vals = [m[key] for m in self.models if m.get(key) is not None]
            return sum(vals) if vals else None

        tin, tout, tcache = total("input_tokens"), total("output_tokens"), total("cache_read_tokens")
        return {
            "run_id": self.run_id, "thread_id": self.thread_id, **({"agent": self.agent} if self.agent else {}),
            **({"choice": self.choice} if self.choice else {}),
            "ttft_ms": round(self.ttft * 1000) if self.ttft is not None else None,
            "total_ms": self._ms(self.t0),
            "model_ms": sum(m["ms"] for m in self.models),
            "tool_ms": sum(t["ms"] for t in self.tools),
            "models": self.models, "tools": self.tools,
            "tokens": {"input": tin, "output": tout, "cache_read": tcache},
            "cache_hit_rate": round(tcache / tin, 3) if tin and tcache is not None else None,
        }


def current() -> RunStats | None:
    """The running turn's collector (None outside a run)."""
    return _current.get()


def activate(stats: RunStats):
    """Make `stats` the current collector; returns a token for `deactivate`."""
    return _current.set(stats)


def deactivate(token) -> None:
    try:
        _current.reset(token)
    except ValueError:   # the stream was closed from another context: nothing to restore there
        pass


def sum_usage(items: list[dict]) -> dict | None:
    """Several calls' usage (LangChain usage_metadata) as one, for a sub-agent that calls its model many times."""
    if not items:
        return None
    out = {"input_tokens": 0, "output_tokens": 0, "input_token_details": {"cache_read": 0, "cache_creation": 0}}
    for u in items:
        out["input_tokens"] += int(u.get("input_tokens") or 0)
        out["output_tokens"] += int(u.get("output_tokens") or 0)
        for k in ("cache_read", "cache_creation"):
            out["input_token_details"][k] += int((u.get("input_token_details") or {}).get(k) or 0)
    return out
