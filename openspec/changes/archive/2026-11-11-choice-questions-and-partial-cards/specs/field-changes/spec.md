## MODIFIED Requirements

### Requirement: One proposal at a time
A turn SHALL have at most one pending card or question. In one model response, a second `propose_changes` or `ask_user` call SHALL be refused, and frontend tools called alongside a card or question SHALL not be executed.

#### Scenario: Two proposals in one response
- **WHEN** the model calls `propose_changes` twice in one response
- **THEN** the second call returns an error and only one card is shown

#### Scenario: A card and a question together
- **WHEN** the model calls `propose_changes` and `ask_user` in one response
- **THEN** only the first one is shown and the other call returns an error

## ADDED Requirements

### Requirement: Partial acceptance
A resume of a field-change card MAY carry `names`, the subset of proposed changes the user kept. Only those changes SHALL count as applied:
- names not on the card SHALL be ignored;
- an empty `names` list SHALL count as a rejection;
- without `names`, an accepted card SHALL apply all changes.

The frontend SHALL send only the kept changes to the form backend.

#### Scenario: Keeping some rows
- **WHEN** a card proposes `first_name`, `last_name` and `gender`, and the user unticks `gender` and accepts
- **THEN** the resume carries `names: ["first_name", "last_name"]`, the model is told `gender` was declined, and the card is recorded as `partial`
