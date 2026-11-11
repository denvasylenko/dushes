# Proposal

## Why

A question tied to a field ("What type of loan do you need?" → "Car loan") is followed by a field-change card for the same value: the user taps twice and makes one decision. This breaks law 2 of the project's UI standard (`ui-craft`, "complex → one tap"). The same audit found smaller debt in the widget:
- font sizes and radii off the scale;
- tap targets under 44 px on phones;
- a hard focus ring left by script focus;
- the server's raw error text shown to users;
- a "Fill in" button that does not say how much it fills;
- a send button that looks primary while empty.

## What Changes

- **Questions that fill their field.** When `ask_user` is tied to a choice field that is editable now, the question card carries:
  - `applies: true`;
  - for each option, its value in the form's own format;
  - the field's previous value.

  A client that applies the answer (the widget's formguide plugin does) sends the chosen value to the form backend and resumes with `{answer, config}`. The agent then treats the field as filled: it gets the form's reaction and does not propose a card for it. The card shrinks to "✓ Car loan · Undo".

  A typed answer, a locked field, or a client that resumes without `config` keeps today's behaviour: the answer, then a card.
- **Widget polish:**
  - type and radius on the `ui-craft` scales;
  - card layout in classes instead of inline styles;
  - 44 px targets on touch screens;
  - a soft keyboard-only focus ring, and no script focus on touch screens;
  - human error messages per kind (network, access, rate limit, server, model) with "Try again" and the raw text in a tooltip;
  - "Fill in 1 field" / "Fill in 3 fields" with plurals per language;
  - a quiet send button while the composer is empty (it stays pressable and shakes);
  - "Still working…" when a turn has shown no text for a few seconds.
- **Demo:** the page title from the form's pack or a readable form name, not the id.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `user-questions`: questions tied to an editable field fill it when the client applies the answer.
- `chat-widget-formguide`: the question card applies such answers, with Undo; field-card labels count the fields.
- `chat-widget`: readable errors, touch-size targets, a slow-turn hint.

## Impact

- Backend: `agent/tools.py` (`ask_user` payload), `agent/graph.py` (the `confirm` ask branch applies), `agent/interaction.py`, `agent/prompts.py`, `guide.py` (transcript `applied`).
- Widget: `src/formguide/cards.ts`, `src/formguide/index.ts`, `src/element.ts`, `src/styles.ts`, i18n (new keys in seven languages), tests.
- Demo: `frontend/src/App.tsx`. Docs: `docs/ui-components.md` §2.5, `docs/chat-widget.md`, `.claude/skills/ui-craft/references/audit.md` (strike out what is fixed).
- Not breaking: new optional payload keys; old clients keep the two-step flow.
