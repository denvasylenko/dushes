## ADDED Requirements

### Requirement: The model can ask a question with options
The agent SHALL offer the model a tool `ask_user` with:
- `question` (required);
- `options` (a list of `{id, label}` or of strings);
- `field` (a field name);
- `multiple` (default false);
- `allow_text` (default true).

A valid call SHALL pause the turn and send a question card to the client.

#### Scenario: A question with the model's own options
- **WHEN** the model calls `ask_user` with question "Is the actual address the same as registration?" and options "Yes" and "No"
- **THEN** the client receives a question card with those two options and the turn waits for the answer

#### Scenario: Free text only
- **WHEN** the model calls `ask_user` with a question and no options
- **THEN** the card has no options and accepts a typed answer

### Requirement: Options from a field
With `field`, the options SHALL come from that field's current choices (dropdown, radio or multiselect) as `{id, label}`, and `multiple` SHALL default to true for a multiselect. With both `field` and `options`, the given options SHALL be a subset of the field's choices, matched by id or label. A field with no choices, a non-choice field, unknown options or more than 12 options SHALL be refused with an explanation to the model, and no card SHALL be sent.

#### Scenario: Asking about a dropdown
- **WHEN** the model calls `ask_user` with `field: loan_type` and the field has 4 options
- **THEN** the card shows those 4 options with their labels, and the card carries `field: "loan_type"`

#### Scenario: Too many options
- **WHEN** the model asks about a field with 40 options
- **THEN** the call is refused, the model is told to narrow the options or ask in text, and no card is sent

### Requirement: The question card payload
The card SHALL be delivered like a field-change card (see agui-protocol), with the value `{type: "ask", card_id, question, options: [{id, label}], multiple, allow_text, field?}`.

#### Scenario: Legacy channel
- **WHEN** the model asks a question and `interrupt_mode` is `legacy`
- **THEN** the client receives `CUSTOM on_interrupt` whose JSON value has `type: "ask"`, and then `RUN_FINISHED`

### Requirement: Answering a question
A resume SHALL answer a question with `{answer: {ids?: [...], text?: "..."}}`; a plain string payload SHALL count as a typed answer. The model SHALL receive the answer as the tool result, naming the chosen labels and ids or quoting the text, and the turn SHALL continue.

#### Scenario: A clicked option
- **WHEN** the user clicks "Car loan" (`auto`) on a card about `loan_type`
- **THEN** the model's next call contains the result "The user chose: Car loan (auto)" and it can propose the field in a card

#### Scenario: A typed answer
- **WHEN** the user types "only on weekends" instead of choosing
- **THEN** the model receives the text as the answer

### Requirement: Invalid or skipped answers
An answer SHALL count as skipped when it has:
- ids not among the card's options;
- several ids without `multiple`;
- text without `allow_text`;
- nothing at all.

A resume with `{accepted: false}` or `status: cancelled` SHALL count as skipped too. On a skip, the model SHALL be told the user skipped the question, with the reason when the answer was invalid.

#### Scenario: Skipped
- **WHEN** the client resumes with `status: cancelled`
- **THEN** the model is told the user skipped the question

#### Scenario: An id that was not offered
- **WHEN** the answer contains an id that is not among the card's options
- **THEN** the question counts as skipped and the model is told the answer was not one of the options

### Requirement: When the model asks
The system prompt SHALL tell the model:
- to use `ask_user` when the user must choose between known options or settle an ambiguity;
- not to use it to confirm field values, because the field-change card does that;
- not to ask again what the user already answered.

#### Scenario: Ambiguous request
- **WHEN** the user says "I want a loan" and the loan type dropdown has several options
- **THEN** the agent asks with a question card tied to `loan_type` instead of listing the options in text
