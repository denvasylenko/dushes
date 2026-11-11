## MODIFIED Requirements

### Requirement: Progress and suggestion events
Besides the existing custom events, a run SHALL send:
- `CUSTOM tool_progress {parent_id, name, input}` for each step of a tool that works in steps, such as the document researcher, while that tool runs;
- `CUSTOM suggestions {items}` (see quick-replies) before `RUN_FINISHED`;
- `CUSTOM run_stats` (see run-observability) as the last event before `RUN_FINISHED` or `RUN_ERROR`.

All of them SHALL validate as AG-UI `CUSTOM` events.

#### Scenario: Research steps
- **WHEN** the model calls `ask_documents` and the researcher searches the documents
- **THEN** the client receives `tool_progress` events whose `parent_id` is the `ask_documents` tool call id

#### Scenario: Stats at the end
- **WHEN** a run finishes
- **THEN** `run_stats` comes right before `RUN_FINISHED`
