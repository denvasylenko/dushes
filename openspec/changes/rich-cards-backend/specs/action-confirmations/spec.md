## ADDED Requirements

### Requirement: Confirmation details
confirm_action MAY take `details: [{label, value}]` (up to 6) and `consequence` (one sentence); they SHALL be passed in the confirm payload.

#### Scenario: Sending an application
- **WHEN** the model confirms with the amount and term as details
- **THEN** the card lists them

### Requirement: Receipt after the action
When a host tool returns a dict with a `receipt` key (`{title?, number?, eta?}`), the system SHALL emit a CUSTOM `receipt` event with the confirmation's card id and those values.

#### Scenario: A submit tool with a number
- **WHEN** submit_application returns `{receipt: {number: "A-118"}}`
- **THEN** a receipt event follows with that number

