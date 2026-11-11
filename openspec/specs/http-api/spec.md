# http-api Specification

## Purpose
Expose the guide to a frontend over HTTP and Server-Sent Events in the AG-UI format, while keeping the core usable without any web framework.

## Requirements

### Requirement: Transport-agnostic core
`FormGuide.run(thread_id, message=…, state=…)` and `FormGuide.run(thread_id, resume=…)` SHALL yield AG-UI-shaped events (`RUN_STARTED`, `TEXT_MESSAGE_START/CONTENT/END`, `CUSTOM` named `ui_directive`, `on_interrupt`, `tool_activity`, `agent_note`, `agent_context`, `memory_compacted`, `RUN_ERROR`, `RUN_FINISHED`) without a web framework.

#### Scenario: Model error
- **WHEN** the provider call fails
- **THEN** a `RUN_ERROR` event with the message is emitted and the stream still ends with `RUN_FINISHED`

### Requirement: Optional FastAPI router
`create_router(guide)` SHALL provide: `POST /layouts` (register a form with optional domain pack), `POST /run` (AG-UI RunAgentInput, SSE; resume via `forwardedProps.command.resume`), `POST /attachments`, `GET /kb/{form_id}`, `POST /kb/{namespace}/documents`, `DELETE /kb/{namespace}/documents/{doc_id}`, `POST /kb/{form_id}/compile`, and a development-only `GET /debug/{thread_id}`.

#### Scenario: Unknown layout
- **WHEN** `/run` is called with a `jsx_hash` that was never registered
- **THEN** the response is 409 asking to register the layout first

### Requirement: Per-message state
Each new message SHALL carry `state = {config, jsx_hash, form_id, ui?, attachments?}`, where `ui` holds active tabs, open accordions, the focused field and the user's local time.

#### Scenario: Relative dates
- **WHEN** the UI state carries the user's local time and the user says "next Tuesday"
- **THEN** the agent resolves the date relative to that time
