# user-questions Specification

## Purpose
Let the agent ask the user one question with clickable options (its own, or a field's choices) and wait for the answer, instead of listing options in text, so decisions take one click and the answer is tied to known ids.

## Requirements

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

### Requirement: Typed answers with an input type
`ask_user` SHALL accept `input: {type, min?, max?}`, where `type` is one of `text`, `number`, `date`, `time` or `datetime`. The card SHALL carry `input`, so a client can show a matching picker. A typed answer SHALL be checked against the type and bounds. A date SHALL be ISO, a time `HH:MM`, a number numeric; an answer that does not match SHALL count as skipped, with the reason. With `field` set to a date or number field and no options, `input` SHALL default to that field's type.

#### Scenario: Asking for a date
- **WHEN** the model asks "When would you like to come?" with `input: {type: "date", min: "2026-11-12"}`
- **THEN** the card carries the input type, and an answer of `"2026-11-20"` reaches the model as typed text

#### Scenario: Out of range
- **WHEN** the answer is a date before `min`
- **THEN** the question counts as skipped and the model is told the date is out of range

### Requirement: Several values are asked as cards, one at a time
The system prompt SHALL tell the model to ask for several values (a person's details) with one card at a time in the form's order (2-3 short text fields together, a question per date, choice or number field), never as a list in prose, without promising a confirmation; and to open a section or show a field without asking for permission.

#### Scenario: The spouse's details
- **WHEN** the user says "Fill the spouse fields now" and six fields are empty
- **THEN** the model asks for the names in one card, not for all six in a paragraph

### Requirement: Dates of birth and issue are in the past
When `ask_user` names a date field whose name says it is in the past (birth, born, dob, issue, issued) and gives no `max`, the question's `input` SHALL carry `max`: today.

#### Scenario: The spouse's date of birth
- **WHEN** the model asks for `spouse_birth_date` with `field` and no input bounds
- **THEN** the card's input is `{type: "date", max: <today>}`

### Requirement: Questions that fill their field
When `ask_user` names a `field` that is a dropdown, radio group or multi-select and is editable now, the question card SHALL carry:
- `applies: true`;
- for each option, its `value` in the form's own format;
- `previous` and `previous_display`, the field's value before the answer.

#### Scenario: Options in the form's format
- **WHEN** the field's component stores only the option id
- **THEN** each option's `value` is its id

### Requirement: Typed answers that fill a text field
When `ask_user` names an editable text field and gives no options, the question card SHALL carry `input: {type: "text"}`, `applies: true`, the field's `label`, `previous` and `previous_display`. Options for a text field SHALL be refused. A resume with `{answer: {text}, config}` SHALL count as the user filling the field (as for an option), and the model SHALL be told not to propose it again; without `config` the text only answers.

#### Scenario: A passport series in one tap
- **WHEN** the model asks "What is your passport series?" with `field: passport_series`, the user types 4444 and the client resumes with the new config
- **THEN** the model's tool result says the user wrote 4444 and that this filled Passport series, and no field-change card follows

### Requirement: An applied answer counts as filling the field
A resume with `{answer: {ids}, config}` SHALL count as the user filling the question's field. The model SHALL be told the field was filled with the chosen option, with the form's reaction (the diff), and SHALL be told not to propose that field again.

#### Scenario: A loan type in one tap
- **WHEN** the model asks "What type of loan do you need?" with `field: loan_type`, and the client applies "Car loan" and resumes with the new config
- **THEN** the model's tool result says `loan_type` was filled with Car loan (auto), followed by the form's changes, and no field-change card follows

### Requirement: Questions that only answer
A question SHALL keep today's behaviour, where the answer is returned and the model proposes the value in a card, when:
- the question has no `field`;
- its field is locked, hidden or read-only;
- the answer is typed text for a choice field;
- the resume carries no `config`.

#### Scenario: A client that does not apply
- **WHEN** a client resumes a question that has `applies: true` with only `{answer: {ids: ["auto"]}}`
- **THEN** the model receives "The user chose: Car loan (auto)", and the field stays as it was

### Requirement: A picker starts at a sensible value
A number or date question MAY carry `input.value`, where the picker starts, only for a value the user or a document already gave, never a guess; the server SHALL keep it inside `min` and `max` (the nearest bound when outside), use the field's own value when the model gives none, and send no `value` when neither exists, so the client does not start at an invented midpoint. A range whose `min` is after its `max` SHALL be refused, so the agent tells the user that no answer fits.

#### Scenario: A licence year
- **WHEN** the agent asks for the licence year with `min` 2028 and a suggested 1988
- **THEN** the picker starts at 2028, not at 1988

### Requirement: Cards in the conversation's language
Everything a user reads on a card SHALL be in the conversation's language: for a field's options the agent SHALL pass `{id, label}` with the label in the user's language, and the server SHALL keep that label with the form's option id; on a field-change card the agent MAY pass each row's `label` and `shown` value in the user's language. The values sent to the form SHALL NOT change.

#### Scenario: A Russian user on an English form
- **WHEN** a user writing in Russian is asked the loan type on an English form
- **THEN** the card's options are in Russian and the chosen value is the form's option id

### Requirement: The options are on the card only
When a turn ends in a question card with options, the words shown before the card SHALL NOT list those options: text that names two or more of them is replaced, before the card appears, by the same text without the list. Text that names fewer than two options SHALL stay as written.

#### Scenario: Services listed and then shown
- **WHEN** the model writes "Which service?" followed by a bulleted list of four services and then asks with a card of the same four
- **THEN** the person sees "Which service?" and the card, and the list appears once, on the card

### Requirement: What counts as the list of options
A bullet list SHALL be removed whole when two or more of its items name an option; a sentence SHALL be removed when it names two or more options; a line left only to introduce the list SHALL go with it. A label SHALL be matched as a whole word, the longest label first, so that a label inside another counts once, and a sentence that names one option SHALL stay.

#### Scenario: A fact about one option
- **WHEN** the text says "Kids haircuts are done only by Maria." and the card offers Haircut, Beard trim and Kids haircut
- **THEN** that sentence stays, because it names one option

### Requirement: A value that was not accepted is not an answered card
When the answer to a question card cannot be taken (the form refuses the value with an error, or the answer is not one the question allows), the run SHALL send `CUSTOM card_result` with `{card_id, status: "not_accepted", reason, field?}`, the card's transcript entry SHALL get that status and reason, and the model SHALL be told that the field is not filled and why. A client SHALL NOT show such a card as answered.

#### Scenario: A VIN of three digits
- **WHEN** the person types "555" into the VIN question and the form answers "17 characters"
- **THEN** the card is marked not accepted with "17 characters", and the agent asks for the VIN again


### Requirement: A client reports the form's refusal
A client that tried a typed answer on the form and was refused SHALL restore the old value and resume with the answer and `rejected: {field name: the form's error text}`, without `config`. The run SHALL treat it as a refused answer: `card_result` with that reason and field, and the model told the field is not filled.

#### Scenario: A VIN of three digits
- **WHEN** the person types "555" into a question card for the VIN and the form says it needs 17 characters
- **THEN** the resume carries `rejected`, the run sends `card_result` `not_accepted` with the form's words, and the reply asks for the VIN again
