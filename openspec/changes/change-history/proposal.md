# Proposal

## Why

After a few cards the user cannot see what the agent changed in the form, and putting an old value back means retyping it. Every accepted change already carries its previous value; the agent should list the changes on request and undo any of them through a card.

## What Changes

- Every accepted card (and every applied answer to a question) is recorded in the thread's change history: field, previous value, new value, when, and whether it came from the agent, a document or the profile.
- A built-in tool `list_changes` lets the agent answer "what did you change?" from the history, newest first.
- "Undo that" / "put the old amount back" makes the agent propose the previous values in an ordinary field-change card (with the fields the form changed because of them); nothing is reverted without the card.
- `GET /threads/{id}/changes?form_id=` returns the history for the page.

## Capabilities

### New Capabilities
- `change-history`: the record of accepted changes per form, answering what changed, and undoing changes through a card.

### Modified Capabilities
(none)

## Impact

- Backend: `agent/graph.py` (record at the confirm node), `agent/tools.py` (`list_changes`, undo through `propose_changes`), `agent/prompts.py`, `server.py` (the endpoint), the transcript store.
- Docs: `concepts/turn.mdx`, `frontend/cards.mdx`, `reference/http-api.md`, `reference/agui-events.md`.
