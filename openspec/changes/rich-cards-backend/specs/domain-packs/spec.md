## ADDED Requirements

### Requirement: Consent fields
A domain pack MAY declare `consents: {field: {required?, doc?: {title, text?, url?}}}`; the same MAY be set in a field spec. Those bool fields SHALL be proposed as consent rows.

#### Scenario: A pack with consents
- **WHEN** the pack marks credit_check as a required consent
- **THEN** proposing it gives a consent row with required true

