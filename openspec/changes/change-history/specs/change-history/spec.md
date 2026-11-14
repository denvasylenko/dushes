# Spec Delta

## Purpose
Keep a record of every change the user accepted in a form, so the agent can say what it changed and put earlier values back through a confirmation card.

## ADDED Requirements

### Requirement: Accepted changes are recorded
Each accepted row of a field-change card and each applied answer SHALL be recorded for the thread and form: `{name, label, previous, value, at, source}` with `source` one of `agent`, `document`, `profile` or `answer`. Rejected rows SHALL NOT be recorded. The history SHALL survive a restart.

#### Scenario: A partly accepted card
- **WHEN** a card proposes amount and term and the user keeps only the amount
- **THEN** the history holds the amount with its previous value and not the term

### Requirement: What did you change
`list_changes(limit?)` SHALL return the history newest first, and the agent SHALL use it to answer questions about earlier changes, naming fields by label.

#### Scenario: Asking later
- **WHEN** after three cards the user asks "what did you change?"
- **THEN** the reply lists the three cards' fields with their old and new values

### Requirement: Undo through a card
A request to undo SHALL make the agent propose the recorded previous values in a field-change card, together with the dependent fields the form changed after them; the values SHALL return only when the card is accepted, and that acceptance SHALL itself be recorded.

#### Scenario: Put the old amount back
- **WHEN** the user says "put the old amount back"
- **THEN** a card proposes the amount's previous value, and after acceptance the history shows both changes

### Requirement: History for the page
`GET /threads/{id}/changes?form_id=` SHALL return the form's history newest first.

#### Scenario: Reading it
- **WHEN** the page requests the loan form's changes after two accepted cards
- **THEN** the response lists those cards' rows, newest first
