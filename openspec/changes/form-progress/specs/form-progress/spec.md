# Spec Delta

## Purpose
Show how far the user is in a form while they fill it, and keep unfinished forms so the user can return to them from any page of the site.

## ADDED Requirements

### Requirement: Progress after every form turn
Each form turn SHALL end with CUSTOM `progress {form_id, title, filled, required, section?}`, where `filled` and `required` count only fillable required fields (as the form context does) and `section` is the open section's title.

#### Scenario: Three fields filled
- **WHEN** the user accepts a card that fills three required fields of the loan form
- **THEN** the run ends with a `progress` event whose `filled` grew by three

### Requirement: The widget shows it
`<agui-chat>` SHALL show the latest `progress` in its header as "<title> · <filled> of <required>" and SHALL hide it on a page without a form.

#### Scenario: The header
- **WHEN** a `progress` event says 12 of 36 for "Loan application"
- **THEN** the header reads "Loan application · 12 of 36"

### Requirement: Drafts of unfinished forms
A form with at least one filled required field and not finished SHALL be kept as a draft of the site thread: `{form_id, title, filled, required, path, updated_at}`. `GET /site/threads/{id}` SHALL return `drafts`. With `Dushes(drafts=fn)`, the host's list SHALL be returned instead.

#### Scenario: Leaving the form
- **WHEN** the user fills 12 of 36 fields and goes to the FAQ page
- **THEN** the thread's `drafts` holds the loan application with 12 of 36

### Requirement: A finished form leaves the drafts
A form submitted through the review card, or reported finished by the host, SHALL be removed from the drafts.

#### Scenario: Submitted
- **WHEN** the user submits the loan form from the review card
- **THEN** `drafts` no longer has it
