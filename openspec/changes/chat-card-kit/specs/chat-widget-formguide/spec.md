## ADDED Requirements

### Requirement: Question variants from the data
The question card SHALL choose its look from the payload and SHALL look as before without that data:
- options with `description`: two-line options;
- 2 or 3 options with the same `attrs` keys: a comparison, with `recommended` marked;
- more than 12 options: a search box, `suggested` options first.

#### Scenario: A comparison from the documents
- **WHEN** three options share `attrs` keys and the answer has sources
- **THEN** they show as columns with a "from the documents" note

#### Scenario: A term with a live payment
- **WHEN** a question about `loan_term` has `input: {type: "number", min: 1, max: 7, step: 1}` and the host gives `preview`
- **THEN** the card shows a stepper, the preview line for the current value, and "Set 5 years", which fills the field with Undo

#### Scenario: No data, no change
- **WHEN** a question has three plain options
- **THEN** it shows three chips, as before

### Requirement: Typed question variants
A question with `input.type` date SHALL show the next days within range plus another-date picker; time SHALL show `slots` or the host's `getSlots`; number with `min` and `max` SHALL show a slider (10 or more steps) or a stepper with the host's `preview`; address SHALL use the host's `lookupAddress`; `fields` SHALL show several inputs in one card. A value chosen this way for a question with `field` SHALL fill the field, with Undo.

#### Scenario: A day
- **WHEN** a question about a date field has `input: {type: "date"}`
- **THEN** the card shows Today, Tomorrow and the next days, and "Other date"

### Requirement: Field card variants
The field card SHALL format a value by its `kind` (numbers grouped, dates in the chat's language, text as is), show a card-level `reason` once, render `consent` rows unticked for the user to tick with a Read toggle for `doc`, show a row `issue` (a warning from the server) with Why, and show a document `source` header with "check" on rows with `confidence: "low"`. On phones its actions SHALL stay in view at the bottom of the card.

#### Scenario: A passport number
- **WHEN** a row has `kind: "text"` and the value 123456
- **THEN** it shows 123456, not 123,456

### Requirement: Review card
An interrupt of type `review` SHALL show sections with what is left and a Continue action in `status` mode, and in `submit` mode the issues: errors with Fix (applies `fix.value` with Undo) and Show, warnings with Why and their source. The main button SHALL name what is left ("Fix 1 to send") until no error remains.

#### Scenario: One error before sending
- **WHEN** the review has one error with a fix and one warning
- **THEN** the button says "Fix 1 to send", and tapping Fix fills the field, marks the row fixed and changes the button to send

### Requirement: Sources, receipt and feedback
`CUSTOM sources` SHALL add source chips under the last answer. A confirm card SHALL show `details` and `consequence`; `CUSTOM receipt` for its card SHALL turn it into a receipt with Copy number. After a confirmed card, with or without a receipt, a thumbs rating SHALL be offered once; it calls `onFeedback` or posts to `{base}/feedback`.

#### Scenario: Sent
- **WHEN** the user confirms sending and the server sends a receipt with a number
- **THEN** the card shows the number with Copy number and the thumbs

### Requirement: Capabilities
The plugin SHALL send `forwardedProps.capabilities`, the list of card variants it renders, with every run.

#### Scenario: A new run
- **WHEN** the chat starts a run
- **THEN** `forwardedProps.capabilities` lists the variants, for example `ask.range` and `review`
