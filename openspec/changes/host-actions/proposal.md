# Proposal

## Why

A host's tools (`SiteTool`) can read the user's data, but every action they take is all-or-nothing text: there is no Undo for a quick action ("mark this request done") and no card for an action the user should finish themselves ("reply in WhatsApp" with a drafted text). The cabinet integration showed the rule that works: reversible one-step actions run at once with Undo; anything irreversible (publishing, sending, money) only leads the user to the host's own button.

## What Changes

- `SiteTool(..., undo=fn)`: a reversible host action. Dushes runs it at once; the run emits CUSTOM `receipt {text, undo_id}` and the chat shows the receipt with Undo; `POST /site/undo/{undo_id}` calls `undo` and the chat confirms.
- A host tool may return `{text, card}` where `card` is a blocks card (from `card-blocks`) with host buttons: for an action the user finishes in the host's UI (open a screen with a drafted reply, a deep link). Dushes never performs an irreversible action itself.
- A tool marked `confirm=True` (for an action with an effect that cannot be undone but must run on the server) is held for a confirmation card before it runs, as `confirm_tools` does for the form agent.
- Dushes' prompt states the rule: reversible → do it and offer Undo; irreversible → prepare and hand the button to the user.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `dushes`: host tools with Undo, host tools that return cards, and confirmation before a held host tool.

## Impact

- Backend: `backend/formguide/site/agent.py` (tool kinds, receipts, cards), `site/guide.py` (the undo endpoint and its store), the prompt.
- Widget: the receipt with Undo exists for confirmed tools; blocks cards exist. Check both render from `/site/run` (coordinate with the UX/UI session).
- Demo: one reversible and one card-returning host tool in `backend/demo/site_app.py`.
- Docs: `backend/dushes.mdx` (host tools section, "Every option"), `reference/agui-events.md`.
