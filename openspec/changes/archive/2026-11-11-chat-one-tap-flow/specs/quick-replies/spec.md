## ADDED Requirements

### Requirement: Suggestions that fill fields
A suggested reply MAY carry field changes. The `suggestions` event SHALL then include `applies`: a list aligned with `items`, each entry null or a list of changes in the field-card shape. Changes SHALL only use values that the user or the assistant named in the last exchange.

#### Scenario: A chip with a value
- **WHEN** the assistant says a 48-month term would lower the payment and the suggestions model returns "Change term to 48 months" with `set: {loan_term: 48}`
- **THEN** the event has `items: ["Change term to 48 months", ...]` and `applies: [[{name: "loan_term", value: <encoded>, display: "48 months", ...}], ...]`

### Requirement: Suggested changes are validated
Each suggested change SHALL be validated against the run's latest form config the same way as a proposal. An invalid change SHALL be dropped and its reply kept as plain text.

#### Scenario: An invalid value
- **WHEN** a suggestion sets a dropdown to an option that does not exist
- **THEN** the reply is sent without changes, and `applies` is omitted when no reply has changes
