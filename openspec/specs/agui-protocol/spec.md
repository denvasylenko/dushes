# agui-protocol Specification

## Purpose
Make formguide a standard AG-UI agent, so any AG-UI client (CopilotKit or another) can connect without adapters.

## Requirements

### Requirement: Valid AG-UI input and encoding
The run endpoint SHALL accept an AG-UI `RunAgentInput` validated with the official AG-UI models (a missing `runId` or message id is filled in) and SHALL encode every event, after validating it, with the official AG-UI encoder as SSE.

#### Scenario: Invalid input
- **WHEN** a body is not a `RunAgentInput`
- **THEN** the endpoint answers 422

### Requirement: Reading the request
The form SHALL be read from `state` (`config`, `jsx_hash`, `form_id`, `ui`, `attachments`). Only a trailing `user` message SHALL count as new text; trailing `tool` messages are frontend tool results; a run ending with an assistant message (e.g. a prefill run) has no new text.

#### Scenario: CopilotKit request
- **WHEN** CopilotKit posts a `RunAgentInput` with the full message list and an empty `tools` list
- **THEN** the run uses the trailing user message and streams valid AG-UI events

### Requirement: Event order
A run SHALL start with `RUN_STARTED` and end with exactly one of `RUN_FINISHED` or `RUN_ERROR`; nothing SHALL follow `RUN_ERROR`. Text SHALL be streamed as `TEXT_MESSAGE_START/CONTENT/END` with matching ids. Each server tool call SHALL be streamed as `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END` and `TOOL_CALL_RESULT`.

#### Scenario: Provider error
- **WHEN** the model call fails mid-run
- **THEN** any open text message is ended, `RUN_ERROR` with the message is the last event, and no `RUN_FINISHED` is sent

### Requirement: Confirmation cards are interrupts
A card SHALL be delivered as an interrupt through the configured channel. Its `type` is one of:
- `set_fields`, a field-change card;
- `ask`, a question (see user-questions);
- `upload`, a file request (see attachment-extraction);
- `confirm`, a confirmation (see action-confirmations).

The channel is `legacy` (default), a `CUSTOM` event `on_interrupt` whose value is a JSON string `{type, card_id, ...}`; `structured`, `RUN_FINISHED.outcome` of type `interrupt`; or `both`.

#### Scenario: Structured shape
- **WHEN** `interrupt_mode` is `structured`
- **THEN** each interrupt is `{id: card_id, reason, message, metadata}`

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

### Requirement: Resuming a card
A run SHALL resume a pending card from `RunAgentInput.resume[]` (`status: resolved` with a payload; `cancelled` means rejected or skipped) or from `forwardedProps.command.resume`. The payloads are:
- for a field-change card: `{accepted, config, names?}`;
- for a question: `{answer: {ids?, text?}}` or a plain string.

#### Scenario: CopilotKit resumes a card
- **WHEN** the client answers an `on_interrupt` card through `forwardedProps.command.resume`
- **THEN** the same turn continues with the user's decision

#### Scenario: AG-UI 1.0 resume
- **WHEN** a client sends `resume: [{interrupt_id: card_id, status: "cancelled"}]`
- **THEN** the card is treated as rejected (or the question as skipped) and the turn continues

#### Scenario: Answering a question
- **WHEN** a client sends `resume: [{interrupt_id: card_id, status: "resolved", payload: {answer: {ids: ["auto"]}}}]`
- **THEN** the turn continues with that answer

### Requirement: Frontend tools
Tools the client declares in `RunAgentInput.tools` SHALL be offered to the model, without shadowing built-in tools. A call to one SHALL be streamed as `TOOL_CALL_START/ARGS/END` with no result, and the run SHALL end so the client can execute it. When the next run carries `tool` messages for those calls, they SHALL be fed back to the model as tool results; calls without a result SHALL be reported to the model as not executed.

#### Scenario: Client-side highlight tool
- **WHEN** the client declares `highlightField` and the model calls it
- **THEN** the client receives the call, runs it, and the next run gives the model its result

### Requirement: AG-UI message export
The transcript of a thread SHALL be exportable as AG-UI messages (user, assistant with tool calls, tool results) so a client can restore its chat with `agent.setMessages`.

#### Scenario: Restore in CopilotKit
- **WHEN** a client fetches `GET /threads/{id}?format=agui`
- **THEN** it receives AG-UI messages in order, including the assistant's replies

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
