## MODIFIED Requirements

### Requirement: Confirmation cards are interrupts
A card SHALL be delivered as an interrupt through the configured channel. There are two kinds: a field-change card (`type: "set_fields"`) and a question card (`type: "ask"`, see user-questions). The channels are:
- `legacy` (default): a `CUSTOM` event `on_interrupt` whose value is a JSON string `{type, card_id, ...}`;
- `structured`: `RUN_FINISHED.outcome` of type `interrupt`, with `{id: card_id, reason, message, metadata}`, where `reason` is `confirm_field_changes` with `metadata {changes}`, or `ask_user` with `metadata {question, options, multiple, allow_text, field?}`;
- `both`.

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
