# chat-history Specification

## Purpose
Keep the conversation the user sees, separately from the model's working history, so it survives compaction, reloads and restarts and can be restored when the user comes back to the form.

## Requirements

### Requirement: Display transcript separate from the model's history
The system SHALL keep, per thread, a display transcript of what the user saw, independent of the history sent to the model. Compaction of the model's history SHALL NOT remove or change transcript entries.

#### Scenario: Long chat after compaction
- **WHEN** the model's history was compacted into a conversation memory
- **THEN** the transcript still contains every earlier user message and assistant reply

### Requirement: What the transcript records
The transcript SHALL record, in order, with an id and a timestamp: user messages with the names of attached files, the assistant's replies (full text, not internal notes; a lead taken back with `text_retract` is kept out), tool activity, confirmation cards with their proposed changes and status, errors, and notices (for example that older turns were summarized for the assistant).

#### Scenario: A turn with a tool and a reply
- **WHEN** the user asks where a field is and the agent focuses it and answers
- **THEN** the transcript gains a user entry, a tool entry and an assistant entry, in that order

### Requirement: Confirmation card status
A card SHALL be recorded as `pending` with a `card_id` that is also sent in the `on_interrupt` event, and its status SHALL change when it is answered or ignored. Question cards SHALL be recorded with the kind `question`, with their question and options.

#### Scenario: Statuses
- **WHEN** a card or question is answered or ignored
- **THEN** its status becomes:
  - for a field-change card: `accepted`, `partial` (with the applied `names`) or `rejected`;
  - for a question card: `answered` (with the answer) or `dismissed`;
  - for either kind: `dismissed` if the user sends a new message instead of answering

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

### Requirement: Start over
The system SHALL allow deleting a thread's transcript and model history.

#### Scenario: New chat
- **WHEN** a thread is deleted
- **THEN** restoring it returns an empty transcript and the next message starts a new conversation

### Requirement: A running turn on restore
`GET /threads/{id}` SHALL include `running: true` while a turn of that thread is still in progress, and `running: false` otherwise.

#### Scenario: Reloading during an answer
- **WHEN** the client restores a thread whose turn is still running
- **THEN** the answer has the transcript so far and `running: true`
