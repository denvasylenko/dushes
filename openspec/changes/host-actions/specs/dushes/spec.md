# Spec Delta

## ADDED Requirements

### Requirement: Host actions with Undo
A `SiteTool` with `undo` SHALL run at once when Dushes calls it, and the run SHALL emit CUSTOM `receipt {text, undo_id}`. `POST /site/undo/{undo_id}` SHALL call `undo(args, ctx)` once and return its text; a second call or an unknown id SHALL return 404. Undo ids SHALL expire after one hour.

#### Scenario: Mark a request done
- **WHEN** the owner says "mark Anna's request as answered" and the host tool `mark_done` has an undo
- **THEN** the request is marked, the chat shows a receipt with Undo, and Undo restores it

### Requirement: Host tools that return a card
A host tool MAY return `{text, card}`; the model SHALL get `text`, and the run SHALL show `card` as a blocks card whose host buttons reach the page as they do for the form agent.

#### Scenario: Reply in WhatsApp
- **WHEN** the owner says "answer Anna that we are open on Sunday" and the tool returns a card with a drafted reply and a "Reply in WhatsApp" link button
- **THEN** the chat shows the card with the draft, and nothing is sent until the owner taps the button

### Requirement: Held host tools
A `SiteTool` with `confirm=True` SHALL NOT run until the user accepts a confirmation card naming the action and its consequence; a rejected card SHALL tell the model the action was not done.

#### Scenario: Unpublish the site
- **WHEN** Dushes calls the held tool `unpublish`
- **THEN** a confirmation card appears, and the tool runs only after the user accepts it

### Requirement: The action rule
Dushes SHALL run reversible host actions without asking and offer Undo, SHALL prepare irreversible ones as cards for the user to finish, and SHALL NOT claim an action was done when its tool failed or was held.

#### Scenario: A failing action
- **WHEN** `mark_done` raises an error
- **THEN** the reply says it could not be done and no receipt is shown
