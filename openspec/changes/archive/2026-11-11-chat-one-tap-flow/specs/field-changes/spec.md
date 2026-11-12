## ADDED Requirements

### Requirement: Dependent fields in one proposal
A dropdown or radio group in a proposal that is disabled, has no options, or lacks the proposed option SHALL become a deferred row instead of an error, when another change in the same proposal is valid and the field has no custom codec. Deferred rows SHALL come last; the client applies them after the other rows.

#### Scenario: Make and model
- **WHEN** the model proposes `car_make: Toyota` and `car_model: Camry` while the model list is empty until a make is chosen
- **THEN** the card has a Make row and a deferred Model row with `lookup: "Camry"` and `after: ["car_make"]`

#### Scenario: Nothing to wait for
- **WHEN** the model proposes only a disabled field
- **THEN** the proposal fails with the reason the field is disabled, as before

### Requirement: The deferred row payload
A deferred row SHALL carry `deferred: true`, `value: null`, `lookup` (the proposed option as text), `display`, `after` (the names of the other rows) and `shape` (how the form stores the option: `option`, `id` or `name`).

#### Scenario: A brand change
- **WHEN** the make changes from Toyota to Kia and the model list still holds Toyota's models
- **THEN** the Model row for "Sportage" is deferred with `after: ["car_make"]`
