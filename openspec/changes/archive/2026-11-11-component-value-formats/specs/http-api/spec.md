## MODIFIED Requirements

### Requirement: Optional FastAPI router
`create_router(guide)` SHALL provide:
- `POST /layouts`: register a form, with an optional domain pack and an optional sample `config`. When a config is given, the response's `warnings` SHALL also include its value warnings;
- `POST /run`: AG-UI RunAgentInput, SSE;
- `POST /prefill`;
- `POST /attachments`;
- `GET /kb/{form_id}`;
- `POST /kb/{namespace}/documents`;
- `DELETE /kb/{namespace}/documents/{doc_id}`;
- `POST /kb/{form_id}/compile`;
- the thread endpoints;
- a development-only `GET /debug/{thread_id}`.

Registered layouts SHALL be kept under the data directory, so clients keep working after a server restart.

#### Scenario: Unknown layout
- **WHEN** `/run` is called with a `jsx_hash` that was never registered
- **THEN** the response is 409 asking to register the layout first

#### Scenario: Server restart
- **WHEN** the server restarts after a form was registered
- **THEN** runs with that `jsx_hash` keep working without registering again

#### Scenario: Checking a sample config
- **WHEN** `POST /layouts` is called with the JSX and the form's initial config, and a dropdown's options have no recognisable keys
- **THEN** the response's `warnings` name that field and suggest setting `option_keys`
