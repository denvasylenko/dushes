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
`CUSTOM ui_directive` events SHALL be passed to `onDirective`. Without `onDirective`, the plugin SHALL scroll to the element with `data-name` (or the input with `name`) equal to the target in the host document, focus it except on touch screens, outline it for a few seconds, and show the directive's `hint` in a bubble under it. Tabs and accordions stay the host's to open.

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
The tools whose result is the card that follows (`propose_changes`, `ask_user`, `request_file`, `confirm_action`) SHALL not appear as separate steps unless `cardSteps` is on. The plugin SHALL provide human-readable step labels for formguide's built-in tools in the chat's language, for example "Searching the business documents" for `ask_documents` and "Reading your document" for `extract_from_attachment`. Hosts MAY override any label.

#### Scenario: A localized step
- **WHEN** the chat language is German and the agent calls `search_fields`
- **THEN** the step shows the German label

### Requirement: One-tap answers
For a question card with `applies: true`, choosing an option SHALL do the following:
- call `applyChanges({field: value})` with the option's value, or with the list of values for a multiple choice;
- resume with `{answer: {ids}, config, ui}`;
- shrink the card to "✓ <label>" with Undo.

If `applyChanges` fails, the card SHALL stay open with the error. Undo SHALL put the previous value back and tell the agent.

#### Scenario: Choosing a loan type
- **WHEN** the user taps "Car loan" on a question card that applies to `loan_type`
- **THEN** `applyChanges` gets `{loan_type: <the option's value>}`, the run resumes with the new config, and the card shows "✓ Car loan" with Undo

### Requirement: Fill-in labels count the fields
A field-change card's main button SHALL say how many fields it fills, with the language's plural form: "Fill in 1 field", "Fill in 3 fields". When some rows are unticked, it SHALL say "Fill in 2 of 3".

#### Scenario: A card with one change
- **WHEN** a card proposes one field
- **THEN** its button reads "Fill in 1 field"

### Requirement: Deferred rows on the card
A deferred row SHALL show its label, the proposed option and a muted "after <field>". Accepting SHALL apply the other kept rows, then look up the deferred row's option in the refreshed form and apply it. A row whose option is not found SHALL show "not available" and SHALL be left out of `names`.

#### Scenario: Make and model in one tap
- **WHEN** the user accepts a card with Make = Toyota and a deferred Model = Camry
- **THEN** the widget applies Make, then Model with the Camry option from the refreshed list, and resumes once

### Requirement: Folded cards
After a field-change card is accepted or rejected, its rows SHALL fold into the result line ("✓ Filled in · Make, Year", with Undo while it lasts). Clicking the line SHALL show or hide the rows.

#### Scenario: A short thread
- **WHEN** the user accepts a card with three rows
- **THEN** the card shows one line with the three labels, and the rows appear on click

### Requirement: Readable values on cards
Number values on cards SHALL be formatted for the chat's language (1500000 -> "1,500,000" in English). A reason equal to the value SHALL be hidden. Question text SHALL render inline markdown (bold, italics, code).

#### Scenario: An amount
- **WHEN** a card proposes `loan_amount` 900000 instead of 1500000 in English
- **THEN** it shows "~~1,500,000~~ 900,000"

### Requirement: Cards show what they filled
After a field-change card, a question card that fills its field, or an action chip is applied, the plugin SHALL send a focus directive for the (last) filled field, with its `reveal` steps and an empty hint, to `onDirective` or the default handling. Question cards tied to a field and suggested changes SHALL carry `reveal` for this.

#### Scenario: A tap on another tab
- **WHEN** the user taps "Kia" on the question "Which car make?" while the Applicant tab is open, and the make field is on the Car tab
- **THEN** the field is filled and the host receives a focus directive for it with the Car tab in `reveal`, so the page opens that tab

