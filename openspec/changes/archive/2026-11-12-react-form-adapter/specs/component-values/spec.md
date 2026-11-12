## ADDED Requirements

### Requirement: Default tags for radio groups and multi-selects
The default component map SHALL include `RadioGroup` (radio) and `MultiSelect` (multi-select), besides the existing default tags.

#### Scenario: A generated skeleton
- **WHEN** a JSX skeleton uses `<RadioGroup name="gender"/>` and `<MultiSelect name="channels"/>` without a `components` configuration
- **THEN** the layout reads them as a radio group and a multi-select, with no unknown-tag warning
