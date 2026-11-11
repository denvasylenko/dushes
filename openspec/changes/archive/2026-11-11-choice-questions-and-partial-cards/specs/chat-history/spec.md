## MODIFIED Requirements

### Requirement: Confirmation card status
A card SHALL be recorded as `pending` with a `card_id` that is also sent in the `on_interrupt` event. Its status SHALL change when the card is answered:
- a field-change card SHALL become `accepted`, `partial` (with the applied `names`) or `rejected` when the turn is resumed;
- a question card SHALL become `answered` (with the answer) or `dismissed` when the turn is resumed;
- either kind SHALL become `dismissed` when the user sends a new message instead.

Question cards SHALL be recorded with the kind `question`, with their question and options.

#### Scenario: Card answered after a reload
- **WHEN** the user reloads the page while a card is pending and then accepts it
- **THEN** the turn resumes and the card's status becomes `accepted`

#### Scenario: Card ignored
- **WHEN** the user sends a new message while a card is pending
- **THEN** the card's status becomes `dismissed`

#### Scenario: Question answered
- **WHEN** the user clicks an option on a question card
- **THEN** the question's status becomes `answered` and the entry records the chosen ids

### Requirement: Restore a conversation
The system SHALL return a thread's transcript and its pending card or question, if any, so a client can show the conversation when the user comes back. The pending item SHALL carry its `kind`. With persistent stores configured, the transcript and the model's history SHALL survive a server restart, and a pending card or question SHALL still be resumable.

#### Scenario: Server restart
- **WHEN** the server restarts with an SQLite checkpointer and a file transcript store, and the user reopens the form
- **THEN** the chat is shown as before and the next message continues the same conversation

#### Scenario: Pending question after a reload
- **WHEN** the user reloads the page while a question is pending
- **THEN** the thread's `pending_card` is the question entry with `kind: "question"`, and answering it resumes the turn
