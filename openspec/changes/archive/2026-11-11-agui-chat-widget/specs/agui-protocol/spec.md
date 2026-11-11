## MODIFIED Requirements

### Requirement: Confirmation cards are interrupts
A card SHALL be delivered as an interrupt through the configured channel. The interrupt types are:
- `set_fields`: a field-change card;
- `ask`: a question (see user-questions);
- `upload`: a file request (see attachment-extraction);
- `confirm`: a confirmation (see action-confirmations).

The channels are:
- `legacy` (default): a `CUSTOM` event `on_interrupt` whose value is a JSON string `{type, card_id, ...}`;
- `structured`: `RUN_FINISHED.outcome` of type `interrupt` with `{id: card_id, reason, message, metadata}`;
- `both`.

#### Scenario: Structured reasons
- **WHEN** `interrupt_mode` is `structured`
- **THEN** the reasons are:
  - `confirm_field_changes` for a field-change card, with `metadata {changes}`;
  - `ask_user` for a question, with `metadata {question, options, multiple, allow_text, input?, field?}`;
  - `request_file` for an upload request;
  - `confirm_action` for a confirmation.

#### Scenario: Default channel
- **WHEN** the agent proposes field values
- **THEN** the client receives `CUSTOM on_interrupt` with a JSON string value of `type: "set_fields"` and then `RUN_FINISHED`

#### Scenario: A question in structured mode
- **WHEN** the agent asks a question and `interrupt_mode` is `structured`
- **THEN** `RUN_FINISHED.outcome.interrupts[0]` has `reason: "ask_user"` and the question in `metadata`

## ADDED Requirements

### Requirement: Progress and suggestion events
Besides the existing custom events, a run SHALL send:
- `CUSTOM tool_progress {parent_id, name, input}` for each step of a tool that works in steps, such as the document researcher, while that tool runs;
- `CUSTOM suggestions {items}` (see quick-replies) before `RUN_FINISHED`.

Both SHALL validate as AG-UI `CUSTOM` events.

#### Scenario: Research steps
- **WHEN** the model calls `ask_documents` and the researcher searches the documents
- **THEN** the client receives `tool_progress` events whose `parent_id` is the `ask_documents` tool call id
