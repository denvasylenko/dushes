# Proposal

## Why

A live session with the demo assistant showed that one user decision often costs several taps and model turns:
- a suggestion chip ("Car is a 2019 Toyota Camry") only sends text, so the value arrives one turn later on a card that needs another tap;
- dependent fields (make -> model) need a card per level, about 25 s for one sentence of the user;
- yes/no decisions ("Should I switch it to 36 months?") come as prose, so the user has to type;
- answered field cards keep their full height, so the thread becomes a column of old cards.

There is also small polish the session surfaced: raw markdown in question cards, unformatted numbers on cards, a reason that repeats the value, an empty state that promises suggestions it does not show, and a replaced card labelled "Skipped".

All of this is generic: it concerns the library and the widget, not one form.

## What Changes

- **Action chips.** A suggested reply MAY carry field changes. The backend validates them like a proposal; a chip with changes fills the fields in one tap (with Undo) and then sends its text, so the agent continues from the filled form.
- **Dependent fields in one card.** `propose_changes` accepts a choice field that has no options yet, or is locked, when the same call changes other fields: the row is applied after them, its option looked up by name in the refreshed form.
- **Prompt rules.** A yes/no or pick-one decision is asked with `ask_user` or proposed as a change, not in prose; a card follows one short sentence that answers the user.
- **Folded cards.** An applied field card folds to one line ("✓ Filled in · Make, Year · Undo"); tapping it shows the rows again.
- **Polish:** inline markdown in question text; locale number formatting on cards; a reason equal to the value is hidden; "New chat" keeps the form's starters; an empty chat without starters does not mention suggestions; a card closed by a new message says "Replaced by your message".

## Capabilities

### Modified Capabilities
- `quick-replies`: suggestions may carry validated field changes.
- `field-changes`: deferred rows for dependent fields.
- `agent-turn`: decision and card-lead rules.
- `chat-widget`: action chips, starters after New chat, empty-state text, replaced cards.
- `chat-widget-formguide`: deferred rows, folded cards, number formatting, question markdown.

## Impact

- Backend: `suggestions.py`, `guide.py`, `agent/tools.py`, `agent/prompts.py`; tests.
- Widget: `element.ts`, `formguide/cards.ts`, `formguide/index.ts`, `styles.ts`, i18n (new keys in seven languages), `types.ts`; tests.
- Docs: `docs/chat-widget.md`, `docs/architecture.md` if the event shape is listed there, `ui-craft` audit.
- Not breaking: `suggestions.items` stays a list of strings; the new `applies` list is optional; old widgets ignore deferred rows' `after`.
