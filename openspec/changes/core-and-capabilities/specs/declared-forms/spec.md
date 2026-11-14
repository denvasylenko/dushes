## ADDED Requirements

### Requirement: A form declared on the server
A form MAY be declared on the server with steps, groups and fields (type, options or a resolver, required, a `when` condition). The UI agent SHALL work on it with the same tools as on a page form, asking groups in order, accepting any value at any time, and asking a conditional field only after its condition holds.

#### Scenario: A value given early
- **WHEN** in the first step the user also gives a value from the third
- **THEN** the value is kept and not asked again later

### Requirement: Dependencies and a changed parent
Dependent options SHALL come from the declaration or from `options(field, values, query)`. When a parent value changes, the server SHALL recompute visibility, required and options, keep still-valid values silently, and clear invalid ones with a note and a Restore action. Validity SHALL be decided by the form or the server, never by the model.

#### Scenario: A new car make
- **WHEN** the user changes the make after picking a model
- **THEN** the model is cleared, the reply says so, and Restore brings both back

### Requirement: A sheet for long forms
A declared form with more than about eight fields in view SHALL open a sheet with its fields beside the chat.

#### Scenario: A long step
- **WHEN** a step has twelve fields
- **THEN** the chat opens the sheet and the agent keeps guiding beside it
