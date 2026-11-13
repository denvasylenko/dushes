## ADDED Requirements

### Requirement: A running turn on restore
`GET /threads/{id}` SHALL include `running: true` while a turn of that thread is still in progress, and `running: false` otherwise.

#### Scenario: Reloading during an answer
- **WHEN** the client restores a thread whose turn is still running
- **THEN** the answer has the transcript so far and `running: true`
