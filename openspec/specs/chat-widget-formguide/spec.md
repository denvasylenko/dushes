# chat-widget-formguide Specification

## Purpose
Connect the chat widget to formguide: send the form with every run, apply the agent's directives through the host, and render formguide's field-change, question, upload and confirmation cards with their configurable features.

## Requirements

### Requirement: The plugin wires the form to the chat
The formguide plugin SHALL take host callbacks:
- `getState()`, which returns `{config, jsx_hash, form_id, ui}`;
- `applyChanges(changes)`, which sends `{name: value}` to the form backend and returns the new config;
- optional `revertChanges(previous)`;
- optional `onDirective(directive)`.

It SHALL send `getState()` as the run `state` before every run, and it SHALL register renderers for the `set_fields`, `ask`, `upload` and `confirm` interrupt types.

#### Scenario: A message from the chat
- **WHEN** the user sends a message
- **THEN** the run's `state` is the host's current form state

### Requirement: Directives reach the host
`CUSTOM ui_directive` events SHALL be passed to `onDirective`. Without `onDirective`, the plugin SHALL open each `reveal` step and scroll to the element with `data-name` equal to the target, in the host document.

#### Scenario: Pointing at a field
- **WHEN** the agent focuses `loan_amount`
- **THEN** `onDirective` receives the directive, with its `reveal` steps and hint

### Requirement: Field-change card
The field-change card SHALL have one row per change, showing the label and the new value. Each part below SHALL be switchable on or off through `fieldCard` options:
- `select`: a checkbox per row, ticked by default;
- `diff`: the old value struck through, when `previous_display` differs;
- `reason`: the agent's reason;
- `edit`: change a value, or pick another option, before accepting;
- `jump`: a button that sends the change's `reveal` as a directive.

#### Scenario: A minimal card
- **WHEN** the host sets `fieldCard: {select: false, diff: false, edit: false, jump: false}`
- **THEN** the card shows only labels, new values and the Fill in and Reject buttons

### Requirement: Accepting a field-change card
Accepting SHALL call `applyChanges` with the kept rows, including edited values, and then resume with `{accepted, config, names?, edited?}`. Rejecting SHALL resume with `{accepted: false}`.

#### Scenario: Edited before accepting
- **WHEN** the user changes the proposed amount from 1500000 to 1200000 and accepts
- **THEN** `applyChanges` gets `loan_amount: 1200000` and the resume carries `edited: {loan_amount: 1200000}`

### Requirement: Undo after applying
When `fieldCard.undo` is on and `revertChanges` is given, an applied card SHALL offer Undo for a few seconds. Undo SHALL call `revertChanges` with the previous values of the applied rows, and send the agent a short user message saying the change was undone.

#### Scenario: Undo
- **WHEN** the user presses Undo on an applied card
- **THEN** `revertChanges` receives the previous values and the agent is told the change was undone

### Requirement: Question card
A question card SHALL show:
- option buttons for a single choice;
- checkboxes and Send for multiple choice;
- a text box when `allow_text`;
- a native picker when `input.type` is date, time, datetime or number.

An answer SHALL resolve with `{answer}`, and Skip with `{accepted: false}`.

#### Scenario: A date question
- **WHEN** the question has `input: {type: "date"}`
- **THEN** the card shows a date picker, and the chosen date is sent as the typed answer

### Requirement: Upload card
An upload card SHALL show a drop zone and a file button that honour `accept` and `multiple`. Files SHALL be uploaded with `POST /attachments` with a progress bar, then the card SHALL resolve with `{attachment_ids}`. Skip SHALL resolve with `{accepted: false}`.

#### Scenario: Uploading a passport
- **WHEN** the agent requests a file with `accept: ".pdf,.jpg"` and the user drops a PDF
- **THEN** the file is uploaded with a progress bar and the run resumes with its attachment id

### Requirement: Confirm card
A confirm card SHALL show a title, a message and two buttons. When `danger` is set, the confirm button SHALL be styled as dangerous. It SHALL resolve with `{accepted}`.

#### Scenario: A dangerous action
- **WHEN** the card has `danger: true`
- **THEN** the confirm button uses the danger colour

### Requirement: Tool labels
The plugin SHALL provide human-readable step labels for formguide's built-in tools in the chat's language, for example "Searching the business documents" for `ask_documents` and "Reading your document" for `extract_from_attachment`. Hosts MAY override any label.

#### Scenario: A localized step
- **WHEN** the chat language is German and the agent calls `search_fields`
- **THEN** the step shows the German label
