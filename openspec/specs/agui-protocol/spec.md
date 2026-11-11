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
A confirmation card SHALL be delivered as an interrupt through the configured channel: `legacy` (default) as a `CUSTOM` event `on_interrupt` whose value is a JSON string `{type, card_id, changes}`; `structured` as `RUN_FINISHED.outcome` of type `interrupt` with `{id: card_id, reason: "confirm_field_changes", metadata: {changes}}`; or `both`.

#### Scenario: Default channel
- **WHEN** the agent proposes field values
- **THEN** the client receives `CUSTOM on_interrupt` with a JSON string value and then `RUN_FINISHED`

### Requirement: Resuming a card
A run SHALL resume a pending card from `RunAgentInput.resume[]` (`status: resolved` with `payload {accepted, config}`; `cancelled` means rejected) or from `forwardedProps.command.resume`.

#### Scenario: CopilotKit resumes a card
- **WHEN** the client answers an `on_interrupt` card through `forwardedProps.command.resume`
- **THEN** the same turn continues with the user's decision

#### Scenario: AG-UI 1.0 resume
- **WHEN** a client sends `resume: [{interrupt_id: card_id, status: "cancelled"}]`
- **THEN** the card is treated as rejected and the turn continues

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
