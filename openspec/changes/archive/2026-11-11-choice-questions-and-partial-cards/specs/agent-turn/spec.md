## MODIFIED Requirements

### Requirement: Confirmation pauses the turn
When the model proposes field values or asks a question, the turn SHALL pause with an `on_interrupt` event carrying the card. A resume SHALL continue the same turn:
- for a field-change card, `{accepted, config, names?}`; on accept the model SHALL receive the form's reaction (diff) as the tool result;
- for a question, the answer (see user-questions).

#### Scenario: Accepted card
- **WHEN** the user accepts a card and the frontend resumes with the rebuilt config
- **THEN** the model's next call contains "The user confirmed; changes applied" and the appeared or unlocked sections

#### Scenario: Partly accepted card
- **WHEN** the user keeps two of three proposed changes and the frontend resumes with `names` of those two and the rebuilt config
- **THEN** the model is told which changes were applied and which the user declined, followed by the form's reaction

#### Scenario: Rejected card
- **WHEN** the user rejects a card
- **THEN** the model is told the changes were rejected and nothing is written

#### Scenario: Ignored card
- **WHEN** the user sends a new message instead of answering a pending card or question
- **THEN** the pending card or question is closed with a tool result saying the user did not answer, before the new message
