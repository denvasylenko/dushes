## ADDED Requirements

### Requirement: Form review tool
The system SHALL offer a review_form tool (when allowed) with `mode` `status` or `submit`, optional `warnings: [{field, message, source?}]` and optional `fixes: {field: value}`. It SHALL pause the turn with an interrupt of type `review`.

#### Scenario: A review before sending
- **WHEN** the model calls review_form with mode submit
- **THEN** the turn waits on a review card

### Requirement: Review content computed by the server
The review payload SHALL carry `mode`, `sections: [{name, label, left, total, reveal}]` over the outermost sections (tabs inside tabs belong to their section), and `issues: [{severity, field, label, message, kind?, fix?, source?, reveal}]`. Form errors (a validation error, a value not in the options) SHALL come from the form state and SHALL always come first; the model's warnings SHALL have severity `warning`. A fix SHALL be validated like a proposed change and dropped when invalid.

#### Scenario: An invalid fix
- **WHEN** the model passes a fix the field does not accept
- **THEN** the issue is shown without a fix

#### Scenario: Nothing to fix
- **WHEN** every required field is filled and valid
- **THEN** the review has no issues and every section has `left` 0

### Requirement: A real error is never crowded out
Required fields that are still empty SHALL NOT be listed as errors one by one. In `status` mode they SHALL appear only in the sections' `left`. In `submit` mode they SHALL follow the form errors as one issue per section (`kind: "missing"`, "N required fields still empty", `field` = the first of them). An empty field the model passes a fix for SHALL get its own row.

#### Scenario: One error behind many empty fields
- **WHEN** the first tabs have 17 empty required fields and the Loan tab has a field with a validation error
- **THEN** the Loan field's error is the first issue in both modes, and in submit mode the empty fields are one row per section

### Requirement: Answering a review
The review SHALL be resumed with `{action: "continue", section?}`, `{action: "submit"}` or `{action: "fixed", names, config}`. A `fixed` resume with a config SHALL be taken like an accepted field-change card (new baseline and version). `submit` SHALL tell the model the user wants to send, so it confirms with confirm_action before the submitting tool.

#### Scenario: Fixes applied
- **WHEN** the user taps Fix on two issues
- **THEN** the resume carries `fixed` with both names and the config, and the agent does not propose those fields again

