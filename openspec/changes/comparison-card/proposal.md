# Proposal

## Why

"Which loan suits me?" or "what is the difference between these two plans?" gets a paragraph today. People compare side by side; the answer should be a card with two or three options, the facts that differ, the recommended one marked and one tap to go ahead. Dushes also cannot ask a clarifying question as a card, which a recommendation needs.

## What Changes

- A comparison card: `show_comparison {title, criteria, options: [{id, title, facts: {criterion: value}, recommended?, why?, action?}]}`; facts come only from the site, the documents, the page context or host tools, and each option may carry an action (`open_form` with a note, or `navigate`).
- Dushes gets `ask_user` (the existing question card) so it can ask up to three questions before recommending.
- An advisor skill for Dushes: ask what matters (amount, term, budget...), compare, recommend with a reason, offer to open the form with the chosen option in the note.
- `<agui-chat>` renders the card (columns on desktop, swipeable options on a phone, the recommended option first and marked).

## Capabilities

### New Capabilities
- `comparison-card`: the comparison card's payload, where its facts may come from, its actions, and how the chat draws it.

### Modified Capabilities
- `dushes`: Dushes can ask questions with the question card and show comparisons.

## Impact

- Backend: the card type and tool (`agent/tools.py` card specs), `site/agent.py` (ask_user and show_comparison for Dushes, resumable cards), an advisor skill in `backend/demo/skills/`.
- Widget: a new renderer in `packages/agui-chat` (coordinate with the UX/UI session); a card-gallery specimen.
- Docs: `frontend/cards.mdx`, `frontend/card-gallery`, `backend/dushes.mdx`, `reference/agui-events.md`.
