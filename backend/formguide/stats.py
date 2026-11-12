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


class RunStats:
    def __init__(self, run_id: str, thread_id: str):
        self.run_id = run_id
        self.thread_id = thread_id
        self.t0 = time.perf_counter()
        self.ttft: float | None = None
        self.models: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []
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
            "kind": kind, "ms": self._ms(started),
            "ttft_ms": round((first_chunk - started) * 1000) if first_chunk else None,
            "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
            "cache_read_tokens": details.get("cache_read"),
        })

    def tool_call(self, name: str, started: float, error: bool = False) -> None:
        if self.span is not None:
            self.span.child("formguide.tool", started, {"formguide.tool.name": name}, error=bool(error))
        self.tools.append({"name": name, "ms": self._ms(started), "error": bool(error)})

    def as_event(self) -> dict[str, Any]:
        def total(key: str) -> int | None:
            vals = [m[key] for m in self.models if m.get(key) is not None]
            return sum(vals) if vals else None

        tin, tout, tcache = total("input_tokens"), total("output_tokens"), total("cache_read_tokens")
        return {
            "run_id": self.run_id, "thread_id": self.thread_id,
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
