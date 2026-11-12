## ADDED Requirements

### Requirement: Actions can be switched off
The system SHALL read `actions` from the config: for each of ask_user, request_file, confirm_action, focus_field, review_form, ask_documents and extract_from_attachment the value `true`, `false` or `auto`. An action that is off SHALL NOT be bound to the model, and the prompt SHALL leave out its rules. The read-only form tools, propose_changes and use_skill are always on.

#### Scenario: An action switched off
- **WHEN** the config has `actions: {request_file: false}`
- **THEN** the model is not offered request_file, and the prompt does not mention asking for files

#### Scenario: Unknown key
- **WHEN** the config has `actions: {upload: false}`
- **THEN** loading the config fails with an error naming the unknown key

### Requirement: Automatic actions
With `auto` (the default for ask_documents, extract_from_attachment and request_file), ask_documents SHALL be on only when the form has business documents, and extract_from_attachment and request_file only when attachments are enabled. The other actions SHALL default to `true`.

#### Scenario: A form without documents
- **WHEN** ask_documents is `auto` and the form has no documents
- **THEN** the model is not offered ask_documents

### Requirement: Client capabilities
A run MAY carry `forwardedProps.capabilities`, a list of names the client can render (e.g. `ask.details`, `ask.multi`, `review`, `sources`, `confirm.receipt`). When the list is present, an action or payload variant that needs a capability the client did not list SHALL be off for that run. When the list is absent, everything the config allows SHALL stay on.

#### Scenario: A client without the review card
- **WHEN** capabilities are sent and do not include `review`
- **THEN** review_form is not bound for that run

#### Scenario: An old client
- **WHEN** no capabilities are sent
- **THEN** the run offers every action the config allows, as before

