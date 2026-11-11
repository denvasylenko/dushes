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
Dropdown values SHALL be accepted as an option id or name and returned as `{id, name}`; checkbox values as booleans or common yes/no words in several languages; dates as `YYYY-MM-DD` or `DD.MM.YYYY` and returned as ISO dates; numbers with spaces or commas.

#### Scenario: Day-first date format
- **WHEN** the model proposes `birth_date = 03.02.1991`
- **THEN** the card value is `1991-02-03`

### Requirement: One proposal at a time
A turn SHALL have at most one pending card; a second proposal in the same step SHALL be refused.

#### Scenario: Two proposals in one response
- **WHEN** the model calls `propose_changes` twice in one response
- **THEN** the second call returns an error and only one card is shown
