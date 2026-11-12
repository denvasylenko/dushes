## ADDED Requirements

### Requirement: Field kind on every change
Every proposed change SHALL carry `kind`, the field's role (text, number, date, select, radio, multiselect, bool, file), so clients can format values by kind.

#### Scenario: A passport number
- **WHEN** a text field holds digits
- **THEN** the change has kind `text`

### Requirement: Consent rows
A proposed change to a bool field marked as a consent SHALL carry `consent: true`, `required` and `doc?: {title, text?, url?}`. Only the rows the user ticked SHALL be applied, and the resume `names` lists them.

#### Scenario: An optional consent left unticked
- **WHEN** the user ticks two of three consents
- **THEN** only the two are applied

### Requirement: Soft issues on rows
propose_changes MAY carry, per change, a short `issue` when a rule or document flags a valid value; the row SHALL then carry `issue: {severity: "warning", message}` (when the client lists `set.issues`). Rules are free text, so the model, not the server, notices them.

#### Scenario: A valid but odd value
- **WHEN** the model proposes an income with the issue "low for the payment"
- **THEN** the row carries that issue as a warning

### Requirement: Document source and confidence
When the proposed values come from the thread's last extraction, the card SHALL carry `source: {kind: "document", title, attachment_id, found}` and each matching change its `confidence`.

#### Scenario: Values from a passport photo
- **WHEN** the model proposes values it got from extract_from_attachment
- **THEN** the card names the document, and a low-confidence value is marked low

