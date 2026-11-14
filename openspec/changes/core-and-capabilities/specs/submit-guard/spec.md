## ADDED Requirements

### Requirement: Submitting only after review and a tap
A tool marked as submitting SHALL NOT be offered to the model until the form's review reports no blockers (no missing required fields, the server accepted the values). It SHALL run only on the resume of its summary card, by that card's id; a user message SHALL never submit, whatever it says.

#### Scenario: A typed "yes"
- **WHEN** the summary card is shown and the user types "yes, send it"
- **THEN** nothing is sent; the card still waits for the tap

#### Scenario: A missing required field
- **WHEN** the user asks to submit with a required field empty
- **THEN** the submitting tool is not available and the agent points to the field
