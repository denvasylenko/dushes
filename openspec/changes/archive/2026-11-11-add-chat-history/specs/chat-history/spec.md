# Spec Delta

## Purpose
Keep the conversation the user sees, separately from the model's working history, so it survives compaction, reloads and restarts and can be restored when the user comes back to the form.

## ADDED Requirements

### Requirement: Display transcript separate from the model's history
The system SHALL keep, per thread, a display transcript of what the user saw, independent of the history sent to the model. Compaction of the model's history SHALL NOT remove or change transcript entries.

#### Scenario: Long chat after compaction
- **WHEN** the model's history was compacted into a conversation memory
- **THEN** the transcript still contains every earlier user message and assistant reply

### Requirement: What the transcript records
The transcript SHALL record, in order, with an id and a timestamp: user messages with the names of attached files, the assistant's replies (full text, not internal notes), tool activity, confirmation cards with their proposed changes and status, errors, and notices (for example that older turns were summarized for the assistant).

#### Scenario: A turn with a tool and a reply
- **WHEN** the user asks where a field is and the agent focuses it and answers
- **THEN** the transcript gains a user entry, a tool entry and an assistant entry, in that order

### Requirement: Confirmation card status
A card SHALL be recorded as `pending` with a `card_id` that is also sent in the `on_interrupt` event. It SHALL become `accepted` or `rejected` when the turn is resumed, and `dismissed` when the user sends a new message instead.

#### Scenario: Card answered after a reload
- **WHEN** the user reloads the page while a card is pending and then accepts it
- **THEN** the turn resumes and the card's status becomes `accepted`

#### Scenario: Card ignored
- **WHEN** the user sends a new message while a card is pending
- **THEN** the card's status becomes `dismissed`

### Requirement: Restore a conversation
The system SHALL return a thread's transcript and its pending card, if any, so a client can show the conversation when the user comes back. With persistent stores configured, the transcript and the model's history SHALL survive a server restart, and a pending card SHALL still be resumable.

#### Scenario: Server restart
- **WHEN** the server restarts with an SQLite checkpointer and a file transcript store, and the user reopens the form
- **THEN** the chat is shown as before and the next message continues the same conversation

### Requirement: Start over
The system SHALL allow deleting a thread's transcript and model history.

#### Scenario: New chat
- **WHEN** a thread is deleted
- **THEN** restoring it returns an empty transcript and the next message starts a new conversation
