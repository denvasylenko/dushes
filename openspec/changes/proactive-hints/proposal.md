# Proposal

## Why

People get stuck silently: a required field left empty for half a minute, an error the form showed, a half-filled form abandoned. The chat waits to be asked. One quiet chip at the right moment ("What goes in 'Company tax ID'?") helps without the annoyance of a popup.

## What Changes

- The page (or `<agui-chat>` with `proactive`) reports moments to the server as a run with `forwardedProps.moment {kind, target?}`: `idle_field` (focus on an empty required field for `idle_seconds`), `form_error` (a validation error appeared), `leaving` (the user goes to another page with a draft open).
- The server answers a moment with at most one chip (a `suggestions` event with one item) made by the cheap model or a fixed text, never with a message, and nothing enters the model's history or the transcript unless the user taps it.
- Limits: off by default (`proactive: {enabled, idle_seconds, max_per_page, kinds}`), never while the user types or a turn runs, at most `max_per_page` chips (default 1), and a dismissed chip is not shown again for that target.

## Capabilities

### New Capabilities
- `proactive-hints`: moments the page reports, the one chip the chat may offer for them, and the limits that keep it quiet.

### Modified Capabilities
(none)

## Impact

- Backend: `backend/formguide/suggestions.py` (a moment's chip), `guide.py` and `site/guide.py` (accept moments), `config.py` (the `proactive` section).
- Widget: moment detection and the chip in `packages/agui-chat` (coordinate with the UX/UI session).
- Docs: `frontend/chat-widget.mdx`, `backend/configuration.mdx`, `reference/configuration.md`, `reference/agui-chat.md`.
