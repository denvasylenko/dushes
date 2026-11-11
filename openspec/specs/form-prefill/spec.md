# form-prefill Specification

## Purpose
Fill a form from data the host application already has (a profile, a previous application, a document) so the user starts from a prefilled form.

## Requirements

### Requirement: Suggest prefill values
`FormGuide.suggest_prefill(state, data=…, text=…, attachments=…)` SHALL return validated values for the form without a chat: data whose keys are field names SHALL be normalized directly; other data, free text and attachments SHALL go through the extraction model. Each value SHALL say whether the field is editable now, and values that fail validation SHALL be reported separately.

#### Scenario: Profile with field names
- **WHEN** the host passes `{"first_name": "Anna", "gender": "Female"}`
- **THEN** the result contains `first_name = "Anna"` and `gender = {id: "f", name: "Female"}`, both editable now

#### Scenario: Value for a locked step
- **WHEN** the host passes a value for a field inside a disabled tab
- **THEN** the value is returned as not editable yet, so it can be applied when the step unlocks

### Requirement: Prefill in the chat
A run with `forwardedProps.prefill = {data?, text?, attachment_ids?}` (or `FormGuide.run(…, prefill=…)`) SHALL let the agent propose the editable values in a confirmation card, keep the others for locked steps, and tell the user what was prefilled. The transcript SHALL record a notice instead of a user message.

#### Scenario: Opening a prefilled conversation
- **WHEN** the app starts a thread with prefill data and no user message
- **THEN** the user sees a card with the known values and a short explanation
