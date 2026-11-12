## ADDED Requirements

### Requirement: Form review tool
The system SHALL offer a review_form tool (when allowed) with `mode` `status` or `submit`, optional `warnings: [{field, message, source?}]` and optional `fixes: {field: value}`. It SHALL pause the turn with an interrupt of type `review`.

#### Scenario: A review before sending
- **WHEN** the model calls review_form with mode submit
- **THEN** the turn waits on a review card

### Requirement: Review content computed by the server
The review payload SHALL carry `mode`, `sections: [{name, label, left, total, reveal}]` over required editable fields per top-level section, and `issues: [{severity, field, label, message, detail?, fix?: {value, display}, source?, reveal}]`. Errors (required empty, validation errors, values not in the options) SHALL come from the form state; the model's warnings SHALL have severity `warning`. A fix SHALL be validated like a proposed change and dropped when invalid.

#### Scenario: An invalid fix
- **WHEN** the model passes a fix the field does not accept
- **THEN** the issue is shown without a fix

#### Scenario: Nothing to fix
- **WHEN** every required field is filled and valid
- **THEN** the review has no issues and every section has `left` 0

### Requirement: Answering a review
The review SHALL be resumed with `{action: "continue", section?}`, `{action: "submit"}` or `{action: "fixed", names, config}`. A `fixed` resume with a config SHALL be taken like an accepted field-change card (new baseline and version). `submit` SHALL tell the model the user wants to send, so it confirms with confirm_action before the submitting tool.

#### Scenario: Fixes applied
- **WHEN** the user taps Fix on two issues
- **THEN** the resume carries `fixed` with both names and the config, and the agent does not propose those fields again

