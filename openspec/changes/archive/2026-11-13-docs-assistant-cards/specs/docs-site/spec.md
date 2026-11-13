## ADDED Requirements

### Requirement: One public host
The docs site, Ask AI and a live demo SHALL be servable from one app (`docs_ai.host`): the site at `/`, the assistant at `/ai`, the demo page at `/demo/` with formguide at `/agent`. The demo SHALL use an inexpensive model, limit messages per conversation (default 15), per address per day and per site per day, and refuse document uploads; answering a card SHALL not count as a message.

#### Scenario: The sixteenth demo message
- **WHEN** a visitor sends a sixteenth message in one demo chat
- **THEN** the run is refused with a sentence that says the chat reached its limit, and no model is called

#### Scenario: A manager tries to upload
- **WHEN** a visitor posts a document to `/agent/kb/...` on the public host
- **THEN** the request is refused with 403
