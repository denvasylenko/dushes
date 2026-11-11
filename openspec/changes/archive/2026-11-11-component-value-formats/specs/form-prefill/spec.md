## MODIFIED Requirements

### Requirement: Suggest prefill values
`FormGuide.suggest_prefill(state, data=…, text=…, attachments=…)` SHALL return validated values for the form without a chat:
- data whose keys are field names SHALL be normalized directly;
- other data, free text and attachments SHALL go through the extraction model.

Each value SHALL be written in the field's own format, like a card value, and SHALL carry a human-readable `display`. Each value SHALL say whether the field is editable now. Values that fail validation SHALL be reported separately.

#### Scenario: Profile with field names
- **WHEN** the host passes `{"first_name": "Anna", "gender": "Female"}` and `gender` has the default dropdown spec
- **THEN** the result contains `first_name = "Anna"` and `gender = {id: "f", name: "Female"}`, both editable now

#### Scenario: A dropdown that stores the id
- **WHEN** `gender` has the field spec `value: id` and the host passes `"Female"`
- **THEN** the result contains `gender = "f"` with display "Female"

#### Scenario: Value for a locked step
- **WHEN** the host passes a value for a field inside a disabled tab
- **THEN** the value is returned as not editable yet, so it can be applied when the step unlocks
