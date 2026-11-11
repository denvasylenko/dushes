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

### Requirement: One proposal at a time
A turn SHALL have at most one pending card; a second proposal in the same step SHALL be refused.

#### Scenario: Two proposals in one response
- **WHEN** the model calls `propose_changes` twice in one response
- **THEN** the second call returns an error and only one card is shown
