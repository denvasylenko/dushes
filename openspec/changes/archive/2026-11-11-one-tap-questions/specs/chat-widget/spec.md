## ADDED Requirements

### Requirement: Readable errors
A failed run SHALL show a sentence for its kind, with "Try again":
- the network is unreachable;
- access is denied (401 or 403);
- too many requests (429);
- the server failed (5xx);
- the model failed (`RUN_ERROR`).

The server's raw message SHALL only be available as a tooltip.

#### Scenario: The server is down
- **WHEN** the run endpoint answers 503
- **THEN** the chat says the assistant could not answer and to try again in a moment, and offers "Try again"

### Requirement: Touch-size targets and quiet focus
On touch screens (`pointer: coarse`), the following SHALL have a tap area of at least 44×44 px:
- icon buttons;
- chips;
- link buttons in cards.

Focus SHALL be shown as a soft ring only for keyboard focus. The widget SHALL not move focus into new cards on touch screens.

#### Scenario: A phone
- **WHEN** the widget runs on a phone
- **THEN** the send, microphone and paperclip buttons are at least 44 px, and a new card does not steal focus

### Requirement: A hint on slow turns
When a run has shown no text for 4 seconds, a quiet "Still working…" line SHALL appear under the typing dots. It SHALL disappear when text or a card arrives.

#### Scenario: A sleeping server
- **WHEN** the first answer takes 6 seconds
- **THEN** "Still working…" is shown from the 4th second until the answer starts
