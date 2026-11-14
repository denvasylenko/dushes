# Spec Delta

## ADDED Requirements

### Requirement: Fields mapped to profile keys
A domain pack MAY carry `profile: {<field name>: <profile key>}`. A field name that is not in the form's layout or a key that is not in `profile.keys` SHALL be reported as a pack warning, like unknown glossary keys.

#### Scenario: A mapping with a typo
- **WHEN** the loan pack maps `mobil` to `phone` and the layout has no `mobil`
- **THEN** loading the pack warns about `mobil`
