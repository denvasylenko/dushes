# Spec Delta

## MODIFIED Requirements

### Requirement: One site conversation that survives a reload
The site thread's transcript SHALL hold every turn the user saw, Dushes' and the form agents' (their text), and the hand-off note, so the note survives a restart. `GET /threads/{id}?form_id=` SHALL return the messages and the open card of that form, for the page to restore the chat after a reload. Each assistant message SHALL carry `agent`: `"dushes"` or `"form"`, the agent that wrote it.

#### Scenario: A reload on the form page
- **WHEN** the user reloads the loan form page in the middle of the conversation
- **THEN** the chat shows the whole conversation again, with the form's open card

#### Scenario: Who answered
- **WHEN** Dushes opens the loan form and the form agent answers in the same run
- **THEN** the thread's two assistant messages carry `agent: "dushes"` and `agent: "form"`
