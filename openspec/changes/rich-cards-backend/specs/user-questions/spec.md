## ADDED Requirements

### Requirement: Option details and comparisons
ask_user options MAY carry `description` (one short line) and `attrs` (a map of short values). The question MAY carry `recommended` (an option id) and `suggested` (up to 5 option ids). The server SHALL drop `attrs` unless at least 2 options share the same keys, and SHALL drop ids in `recommended` or `suggested` that are not options.

#### Scenario: Attributes on one option only
- **WHEN** only one option has attrs
- **THEN** the payload carries no attrs

#### Scenario: A suggested id that is not an option
- **WHEN** suggested lists an unknown id
- **THEN** that id is dropped

### Requirement: Long field-backed lists
A question with `field` and no `options` SHALL carry all of the field's current options, up to 500. Options the model writes itself SHALL stay limited to 12.

#### Scenario: A bank list
- **WHEN** the model asks about a field with 214 options and passes no options
- **THEN** the card carries all 214 options

### Requirement: Number ranges from the field
A typed number question about a field SHALL carry `min`, `max`, `step` and `unit` from the field when the form defines them; the model MAY narrow min and max.

#### Scenario: A term field
- **WHEN** the term field allows 1 to 7 years in steps of 1
- **THEN** the question carries min 1, max 7, step 1 and the unit

### Requirement: Address input
`input.type` MAY be `address`; the answer SHALL be typed text, checked only for being non-empty.

#### Scenario: An address question
- **WHEN** the model asks with input type address
- **THEN** the card carries `input: {type: "address"}`

### Requirement: Several fields in one question
ask_user MAY carry `fields: [{name, label?, input?, required?}]` with 2 or 3 editable fields (when the client lists `ask.multi`). The server SHALL fill label and input from each field. The resume `{answers: {name: value}, config}` SHALL be validated like proposed changes and taken like an accepted card; answers that fail are reported to the model.

#### Scenario: A client without ask.multi
- **WHEN** the model passes fields and the client did not list `ask.multi`
- **THEN** the tool returns an error and the model asks one question at a time

#### Scenario: Two names in one card
- **WHEN** the user types first and last name and sends
- **THEN** both fields are filled and the agent does not propose them again

