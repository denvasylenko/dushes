"""AG-UI wire adapter: RunAgentInput -> FormGuide.run() arguments, events -> SSE.

`FormGuide.run()` yields AG-UI events as plain dicts, so the core has no web dependency.
This module (needs the `ag-ui-protocol` package, extra `server`) validates the input and
every outgoing event against the official AG-UI models and encodes them.

    kwargs = run_kwargs(body)                       # body = the JSON a client POSTed
    async for ev in guide.run(**kwargs):
        yield encode(ev)

How a request is read:
- `state` carries the form: {config, jsx_hash, form_id, ui?, attachments?};
- a trailing `user` message is the user's text (a run that ends with an assistant message,
  e.g. a prefill run, has no new text); trailing `tool` messages (after the last
  assistant message) are results of frontend tools and make the run a continuation;
- `tools` are frontend tools the client can run (CopilotKit actions, HttpAgent tools);
- a card is answered with `resume: [{interrupt_id, status, payload}]` (AG-UI 1.0;
  `cancelled` = rejected) or `forwardedProps.command.resume` (CopilotKit / ag-ui-langgraph);
- `forwardedProps.prefill = {data?, text?, attachment_ids?, language?}` starts a prefilled turn.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from ag_ui.core import Event, RunAgentInput
from ag_ui.encoder import EventEncoder
from pydantic import TypeAdapter

log = logging.getLogger("formguide")
_EVENT = TypeAdapter(Event)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):   # multimodal user content: keep the text parts
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def _resume_value(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            # plain text: a typed answer to a question; on a field-change card "yes" / "ok" counts as accept
            raw = {"answer": {"text": raw}}
    if isinstance(raw, bool):
        return {"accepted": raw}
    return raw if isinstance(raw, dict) else {"accepted": False}


def run_kwargs(body: dict[str, Any]) -> dict[str, Any]:
    """Validate an AG-UI RunAgentInput and map it to FormGuide.run() keyword arguments."""
    body = {**body, "runId": body.get("runId") or str(uuid.uuid4()),   # forgiving for hand-written clients
            "messages": [{"id": m.get("id") or f"m{i}", **m} for i, m in enumerate(body.get("messages") or [])]}
    inp = RunAgentInput.model_validate(body)
    fwd = inp.forwarded_props if isinstance(inp.forwarded_props, dict) else {}
    msgs = [m.model_dump(by_alias=True) for m in inp.messages]

    resume = None
    if inp.resume:
        r = inp.resume[0]
        resume = _resume_value(r.payload) if r.status == "resolved" else {"accepted": False}
        if r.status == "resolved" and r.payload is None:
            resume = {"accepted": True}
    elif (fwd.get("command") or {}).get("resume") is not None:
        resume = _resume_value(fwd["command"]["resume"])

    message, tool_results = None, None
    if resume is None and msgs:
        if msgs[-1].get("role") == "tool":
            tool_results = {}
            for m in reversed(msgs):
                if m.get("role") != "tool":
                    break
                tool_results[m["toolCallId"]] = _text(m.get("content"))
        elif msgs[-1].get("role") == "user":   # only a trailing user message is new input
            message = _text(msgs[-1].get("content"))

    tools = [{"name": t.name, "description": t.description, "parameters": t.parameters} for t in inp.tools or []]
    return {"thread_id": inp.thread_id, "run_id": inp.run_id, "message": message,
            "state": inp.state if isinstance(inp.state, dict) else {}, "resume": resume,
            "client_tools": tools, "tool_results": tool_results, "prefill": fwd.get("prefill"),
            "capabilities": fwd.get("capabilities"),
            **({"trace_context": {k: str(fwd[k]) for k in ("traceparent", "tracestate") if fwd.get(k)}}
               if fwd.get("traceparent") else {})}


def encoder(accept: str | None = None) -> EventEncoder:
    return EventEncoder(accept=accept)


def encode(ev: dict[str, Any], enc: EventEncoder | None = None) -> str:
    """One event as SSE, validated against the AG-UI event models."""
    try:
        return (enc or EventEncoder()).encode(_EVENT.validate_python(ev))
    except Exception as e:  # noqa: BLE001 — never break the stream over one event
        log.error("invalid AG-UI event %s: %s", ev.get("type"), e)
        return f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
