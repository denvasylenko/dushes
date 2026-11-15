# field-changes Specification

## Purpose
Let the agent fill form fields safely: the config belongs to the form backend, so the agent proposes values, the user confirms, and the frontend applies them through the same path as manual input.

## Requirements

### Requirement: The agent never writes the config
Field values SHALL change only through a confirmation card: the frontend applies accepted values as form events to the form backend, which rebuilds the config.

#### Scenario: Accepted proposal
- **WHEN** the user accepts a card with `loan_type = auto`
- **THEN** the frontend sends the change to the form backend and resumes the turn with the new config

### Requirement: Proposals are validated before the card
Each proposed change SHALL be checked against the current config. Changes to unknown names, containers, hidden, disabled or read-only fields, file fields, or values not among a dropdown's options SHALL be dropped with an explanation returned to the model; if no change passes, no card SHALL be shown.

#### Scenario: Mixed proposal
- **WHEN** the model proposes `loan_type = auto` and a value for the read-only `age`
- **THEN** the card contains only `loan_type` and the model is told `age` is read-only

#### Scenario: Locked field
- **WHEN** the model proposes a field inside a disabled tab
- **THEN** no card is shown and the model gets the reason (learned or GUESS)

### Requirement: Values are normalized
A proposed value SHALL be checked against the field's role and written in the field's own format (see component-values). Each card change SHALL also carry `display`, the value as human text.

#### Scenario: Accepted inputs
- **WHEN** the model proposes a value
- **THEN** each field type accepts the following:
  - a dropdown or radio: an option id or label;
  - a multiselect: a list or a comma-separated text of ids or labels, each validated;
  - a checkbox: a boolean or a common yes/no word in several languages;
  - a date: `YYYY-MM-DD` or `DD.MM.YYYY`;
  - a number: digits with spaces or commas.

#### Scenario: Default written formats
- **WHEN** the field uses the default spec of its role
- **THEN** the value is written as:
  - a dropdown or radio: `{id, name}`;
  - a multiselect: a list of those;
  - a date: an ISO date;
  - a number: a JSON number.

#### Scenario: Day-first date format
- **WHEN** the model proposes `birth_date = 03.02.1991` for a date field with the default spec
- **THEN** the card value is `1991-02-03`

#### Scenario: Number with spaces
- **WHEN** the model proposes `loan_amount = 250 000` for a number field with the default spec
- **THEN** the card value is the JSON number `250000` and the display is `250000`

#### Scenario: A dropdown that stores the id
- **WHEN** the field spec has `value: id` and the model proposes the label "Car loan" of option `auto`
- **THEN** the card value is `"auto"` and the display is "Car loan"

### Requirement: Clearing a field
A change whose value is an empty string or null SHALL propose clearing that field: the card row SHALL carry `value: null` (`[]` for a multiselect), `display: "—"`, `cleared: true` and the previous value, and the field SHALL be emptied only when the card is accepted. Clearing a field that is already empty, disabled or read-only SHALL be refused to the model; a checkbox is set to false, not cleared.

#### Scenario: The user takes a value back
- **WHEN** the loan purpose is "Home renovation" and the model proposes `loan_purpose = ""` because the user asked to clear it
- **THEN** the card shows the purpose being cleared, and after acceptance the field is empty

### Requirement: One proposal at a time
A turn SHALL have at most one pending card or question. In one model response, a second `propose_changes` or `ask_user` call SHALL be refused, and frontend tools called alongside a card or question SHALL not be executed.

#### Scenario: Two proposals in one response
- **WHEN** the model calls `propose_changes` twice in one response
- **THEN** the second call returns an error and only one card is shown

#### Scenario: A card and a question together
- **WHEN** the model calls `propose_changes` and `ask_user` in one response
- **THEN** only the first one is shown and the other call returns an error

### Requirement: Partial acceptance
A resume of a field-change card MAY carry `names`, the subset of proposed changes the user kept. Only those changes SHALL count as applied:
- names not on the card SHALL be ignored;
- an empty `names` list SHALL count as a rejection;
- without `names`, an accepted card SHALL apply all changes.

The frontend SHALL send only the kept changes to the form backend.

#### Scenario: Keeping some rows
- **WHEN** a card proposes `first_name`, `last_name` and `gender`, and the user unticks `gender` and accepts
- **THEN** the resume carries `names: ["first_name", "last_name"]`, the model is told `gender` was declined, and the card is recorded as `partial`

### Requirement: Previous values on cards
Each card change SHALL carry `previous` and `previous_display`: the field's value before the change, in the form's own format and as human text. Both SHALL be null when the field was empty.

#### Scenario: Changing a filled field
- **WHEN** the agent proposes `first_name = Anna` while the field holds `Ana`
- **THEN** the change has `previous: "Ana"`, `previous_display: "Ana"` and `display: "Anna"`

### Requirement: Values edited on the card
A field-change resume MAY carry `edited: {name: value}` for values the user changed on the card before accepting. The frontend SHALL apply the edited values instead of the proposed ones. The model SHALL be told which values the user edited, and the form's reaction SHALL be judged from the new config as usual.

#### Scenario: The user corrects an amount
- **WHEN** the resume has `edited: {loan_amount: 1200000}`
- **THEN** the model's tool result says the user changed `loan_amount` to 1200000 before applying it

### Requirement: Dependent fields in one proposal
A dropdown or radio group in a proposal that is disabled, has no options, or lacks the proposed option SHALL become a deferred row instead of an error, when another change in the same proposal is valid and the field has no custom codec. Deferred rows SHALL come last; the client applies them after the other rows.

#### Scenario: Make and model
- **WHEN** the model proposes `car_make: Toyota` and `car_model: Camry` while the model list is empty until a make is chosen
- **THEN** the card has a Make row and a deferred Model row with `lookup: "Camry"` and `after: ["car_make"]`

#### Scenario: Nothing to wait for
- **WHEN** the model proposes only a disabled field
- **THEN** the proposal fails with the reason the field is disabled, as before

### Requirement: The deferred row payload
A deferred row SHALL carry `deferred: true`, `value: null`, `lookup` (the proposed option as text), `display`, `after` (the names of the other rows) and `shape` (how the form stores the option: `option`, `id` or `name`).

#### Scenario: A brand change
- **WHEN** the make changes from Toyota to Kia and the model list still holds Toyota's models
- **THEN** the Model row for "Sportage" is deferred with `after: ["car_make"]`

### Requirement: No card for a value the field already has
A proposed value equal to the field's current value (as the user sees it) SHALL NOT become a card row; the agent SHALL be told the field already has it, and a proposal of only such values SHALL make no card.

#### Scenario: Gender is already set
- **WHEN** the user asks to fill in gender and it is already Male, and the agent proposes Male
- **THEN** no "Filled in" card appears and the agent says gender is already set

### Requirement: A consent is the person's own tick
A checkbox is a consent when the pack lists it in `consents`, the form marks it `consent: true`, or its label reads as an agreement, an acceptance of terms or a declaration; `consent: false` on the field says it is not. On a field-change card such a row SHALL be a consent row, shown unticked, and it SHALL be applied only when the answer names it in `names`: an answer that accepts everything, or a typed "yes", never applies it.

#### Scenario: Accept all on a card with the terms
- **WHEN** a card holds the first name and "I accept the rental terms", and the answer is `{accepted: true}` with no `names`
- **THEN** the first name is applied, the terms are not, and the model is told the consent was not ticked

### Requirement: The agent cannot give a consent
When the client cannot show a consent row, a proposal for a consent field SHALL be refused, and the model is told that only the person gives it, with their own tick in the form or their answer to a question about that field.

#### Scenario: A client without consent rows
- **WHEN** the client lists capabilities without `set.consent` and the model proposes `accept_terms = true`
- **THEN** no card is shown and the tool result says the field is a consent only the person gives

### Requirement: A question about a consent fills it
A question card that asks the person to agree, accept or consent, while the form has a visible consent not yet given, SHALL be bound to that consent's field, so that the person's own yes fills it; that card SHALL carry `consent: true`, the consent's own text as `label` and its document as `doc` when it has one. Such a question without a field SHALL be refused, and the model is told which consent fields are open.

#### Scenario: Asked before sending
- **WHEN** the form has a required "I agree to the cancellation policy" checkbox and the model asks "Do you agree to the cancellation policy?" with Yes and No and no field
- **THEN** the tool refuses and names the checkbox, the model asks again with that field, and the person's Yes ticks it
