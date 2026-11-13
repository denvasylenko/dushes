## ADDED Requirements

### Requirement: A running turn after a reload
When a restore reports `running: true`, the chat SHALL show the restored messages and a "Still answering…" line, check the thread again every 2 seconds, and when the turn has ended SHALL restore again, showing the answer and any pending card, without a reload.

#### Scenario: Back after a reload
- **WHEN** the user reloads while the agent is answering
- **THEN** the chat shows the conversation with "Still answering…", and the answer appears when the turn ends

### Requirement: Stop reaches the server
The chat's Stop SHALL also post `/stop` with the thread id, so the turn ends on the server and not only in the browser.

#### Scenario: Stop
- **WHEN** the user presses Stop while the agent answers
- **THEN** the plugin posts `{thread_id}` to `<base>/stop`
