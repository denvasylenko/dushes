## ADDED Requirements

### Requirement: Typed answers with an input type
`ask_user` SHALL accept `input: {type, min?, max?}`, where `type` is one of `text`, `number`, `date`, `time` or `datetime`. The card SHALL carry `input`, so a client can show a matching picker. A typed answer SHALL be checked against the type and bounds. A date SHALL be ISO, a time `HH:MM`, a number numeric; an answer that does not match SHALL count as skipped, with the reason. With `field` set to a date or number field and no options, `input` SHALL default to that field's type.

#### Scenario: Asking for a date
- **WHEN** the model asks "When would you like to come?" with `input: {type: "date", min: "2026-11-12"}`
- **THEN** the card carries the input type, and an answer of `"2026-11-20"` reaches the model as typed text

#### Scenario: Out of range
- **WHEN** the answer is a date before `min`
- **THEN** the question counts as skipped and the model is told the date is out of range
