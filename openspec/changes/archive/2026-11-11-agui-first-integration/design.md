# Design

## Context

AG-UI is the contract between agent backends and UIs; CopilotKit is its most common client. CopilotKit currently resumes LangGraph-style interrupts through `forwardedProps.command.resume` after a `CUSTOM` `on_interrupt` event whose value is a JSON string (the `ag-ui-langgraph` convention). AG-UI 1.0 adds structured interrupts (`RunFinishedEvent.outcome = {type: "interrupt", interrupts: [...]}`) and `RunAgentInput.resume[]`; clients that see the structured outcome stop sending the legacy resume, so emitting both by default would strand older clients.

## Goals / Non-Goals

**Goals:** strict AG-UI on the wire; works with CopilotKit without adapters; frontend tools; prefill; a five-minute setup.
**Non-Goals:** AG-UI `STATE_SNAPSHOT/DELTA` of the form config (the client owns the config; patching unknown client state is unsafe); a CopilotKit runtime of our own.

## Decisions

- **Encoding in the router, events built in `guide.run`.** `guide.run` keeps yielding plain dicts (no web dependency in the core); `agui.py` validates them against the `ag_ui.core` event union and encodes them with `EventEncoder` (SSE; the Python encoder has no protobuf).
- **Interrupt channels.** `interrupt_mode = "legacy" | "structured" | "both"` (default `legacy`). The `on_interrupt` value is a JSON string of `{type, card_id, changes}`; the structured outcome uses `Interrupt{id: card_id, reason: "confirm_field_changes", metadata: {changes}}`. Resume accepts `resume[{interrupt_id, status, payload}]` (`cancelled` = rejected) or `forwardedProps.command.resume`.
- **Tool activity as AG-UI tool calls.** Server tools are announced as tool calls with their result (`TOOL_CALL_RESULT`), so clients render them with standard renderers. A client tool call has no result event: the client runs it.
- **Frontend tools round trip.** Client tools are bound next to the built-in ones (client names never shadow built-ins). When the model calls one, the graph stores the pending call ids and ends the turn. The next run delivers `tool` messages; `sync` turns them into tool results (missing ones become "not executed") before any new user message.
- **Prefill reuses extraction.** Known data whose keys are field names is normalized directly; other data, text and attachments go through the extraction call. `suggest_prefill` returns validated values (editable now / later) for server-side use; the chat variant hands them to the agent, which proposes the editable ones and keeps the rest for locked steps.
- **Layouts on disk.** Registered JSX is written to `<data_dir>/layouts/<hash>.jsx` and loaded on demand, so a restart does not break clients holding a `jsx_hash`.
- **Packaging.** Core dependencies: langgraph, langchain, langchain-core, pydantic, pyyaml, pypdf. Everything else is an extra; imports of optional packages are lazy.

## Risks / Trade-offs

- Two interrupt channels to maintain until CopilotKit adopts `resume[]`; default stays legacy.
- Frontend tools add a turn boundary; the agent's context is rebuilt from the config sent with the continuation run.
