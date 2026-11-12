# http-api Specification

## Purpose
Expose the guide to a frontend over HTTP and Server-Sent Events in the AG-UI format, while keeping the core usable without any web framework.

## Requirements

### Requirement: Transport-agnostic core
`FormGuide.run(thread_id, message=…, state=…, client_tools=…, tool_results=…, prefill=…)` and `FormGuide.run(thread_id, resume=…)` SHALL yield AG-UI events as plain dicts (`RUN_STARTED`, `TEXT_MESSAGE_START/CONTENT/END`, `TOOL_CALL_START/ARGS/END`, `TOOL_CALL_RESULT`, `CUSTOM` named `ui_directive`, `on_interrupt`, `agent_note`, `agent_context`, `memory_compacted`, then `RUN_FINISHED` or `RUN_ERROR`) without a web framework.

#### Scenario: Model error
- **WHEN** the provider call fails
- **THEN** open text messages are ended and `RUN_ERROR` with the message is the last event

### Requirement: Optional FastAPI router
`create_router(guide)` SHALL provide:
- `POST /layouts`, which takes an optional domain pack and an optional sample `config`;
- `POST /run` (AG-UI, SSE);
- `POST /prefill`;
- `POST /attachments`;
- the knowledge-base endpoints under `/kb`;
- the thread endpoints;
- a development-only `GET /debug/{thread_id}`.

Registered layouts SHALL be kept under the data directory, so clients keep working after a server restart.

#### Scenario: Knowledge-base endpoints
- **WHEN** the router is mounted
- **THEN** it serves `GET /kb/{form_id}`, `POST /kb/{namespace}/documents`, `DELETE /kb/{namespace}/documents/{doc_id}` and `POST /kb/{form_id}/compile`

#### Scenario: Unknown layout
- **WHEN** `/run` is called with a `jsx_hash` that was never registered
- **THEN** the response is 409 asking to register the layout first

#### Scenario: Server restart
- **WHEN** the server restarts after a form was registered
- **THEN** runs with that `jsx_hash` keep working without registering again

#### Scenario: Checking a sample config
- **WHEN** `POST /layouts` is called with the JSX and the form's initial config, and a dropdown's options have no recognisable keys
- **THEN** the response's `warnings` name that field and suggest setting `option_keys`

### Requirement: Per-message state
Each new message SHALL carry `state = {config, jsx_hash, form_id, ui?, attachments?}`, where `ui` holds active tabs, open accordions, the focused field and the user's local time.

#### Scenario: Relative dates
- **WHEN** the UI state carries the user's local time and the user says "next Tuesday"
- **THEN** the agent resolves the date relative to that time

### Requirement: Thread endpoints
The router SHALL provide `GET /threads/{thread_id}` returning `{transcript, pending_card}` and `DELETE /threads/{thread_id}` removing the thread's transcript and model history. Invalid thread ids SHALL be rejected with 400.

#### Scenario: Restoring a thread
- **WHEN** a client calls `GET /threads/{thread_id}` for a thread with a pending card
- **THEN** the response contains the full transcript and that card in `pending_card`

### Requirement: Prefill endpoint
The router SHALL provide `POST /prefill` with `{state, data?, text?, attachment_ids?, thread_id?}` returning the validated prefill suggestions.

#### Scenario: Server-side prefill
- **WHEN** a backend posts a profile for a form before showing it
- **THEN** it receives the values it can apply now and those for later steps

### Requirement: AG-UI thread export
`GET /threads/{thread_id}?format=agui` SHALL return the thread as AG-UI messages; without the parameter the endpoint keeps returning the transcript.

#### Scenario: Export
- **WHEN** a client requests `format=agui`
- **THEN** the response is `{messages: [...]}` in AG-UI message format

### Requirement: Debug view of a thread
The development-only `GET /debug/{thread_id}` SHALL return:
- the model's history for the thread;
- `runs`: the stats of the thread's most recent runs (see run-observability).

It SHALL only be mounted when the router is created with `debug=True`.

It SHALL be off by default, both in `create_router` and in `create_app`.

#### Scenario: Debug off
- **WHEN** the router is created with `debug=False`
- **THEN** `GET /debug/{thread_id}` is not found

#### Scenario: Debug off by default
- **WHEN** the router is created as `create_router(guide)`
- **THEN** `GET /debug/{thread_id}` is not found

### Requirement: Bounded chat inputs
The router SHALL not authenticate callers; that is the host application's job. It SHALL bound what one request can make it hold:
- `POST /layouts` SHALL refuse a layout over 2,000,000 characters with 413;
- `POST /attachments` SHALL read at most one byte past the attachment store's size limit, and refuse a larger file with 400, without reading it whole into memory.

#### Scenario: Oversized attachment
- **WHEN** a client uploads a file larger than the attachment size limit
- **THEN** the request fails with 400 saying the file is too large, and nothing is stored

#### Scenario: Oversized layout
- **WHEN** a client registers a layout over the size limit
- **THEN** the request fails with 413 and nothing is stored
