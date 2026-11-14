# Spec Delta

## ADDED Requirements

### Requirement: Continue an unfinished form
On a page without a draft's form, Dushes SHALL know the thread's drafts; with suggestions on it SHALL offer "Continue <title>" once per page, and a request to continue SHALL call `open_form` for that form with a note to continue where the user left off.

#### Scenario: Back from the FAQ
- **WHEN** the loan application is a draft and the user on the FAQ page says "let's finish the application"
- **THEN** Dushes opens the loan form and the form agent continues from the first empty required field
