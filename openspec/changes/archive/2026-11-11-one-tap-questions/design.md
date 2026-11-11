# Design

## Mini-brief (ui-craft)

1. **Who and why.** A person fills the loan form with the assistant and picks a loan type.
2. **Main action.** Tap the option.
3. **Tap ladder.** 2 today (the option, then "Fill in") → 1 (the option), with Undo at hand.
4. **States.** A locked field or a typed answer: a card as today. A form-backend error: shown in the card, which stays open. A client without the plugin: a card as today.
5. **Phone.** Chips and links have a 44 px tap area, and new cards do not steal focus.

## Decisions

- **The server says whether the question applies.** It knows if the field is editable and how the component stores values (`component-values`). The card therefore carries `applies` and each option's encoded `value`. For a multiselect each option's value is the encoding of that single item, and the client sends the list. The client never encodes values itself.
- **One resume shape.** `{answer: {ids}, config}` means "applied", and `{answer}` alone means "answered". In `confirm`, the ask branch reuses the field-card path: `compute_diff` with `agent_names = {field}`, `deps.observe`, a new snapshot and version. The answer text goes first, followed by "It is filled into <label>; do not propose it again."
- **Undo.** It uses the card's `previous` and the plugin's `revertChanges` (falling back to `applyChanges`), then sends a short user message, as the field card's Undo does.
- **Errors.** The kind comes from what failed:
  - `fetch` failing → network;
  - an HTTP status → access, rate or server;
  - `RUN_ERROR` → model.

  The raw text goes into `title`.
- **Plurals.** `Intl.PluralRules(lang).select(n)` picks `fields_one|few|many|other`, and every language defines the forms it needs.
- **Scales.** Font sizes go to 11 / 12 / 13 / 15 / 17 / 28 (16 on inputs). Radii go to 6 / 10 / 14 / 20 / 999, with the `--agui-radius` default becoming 14.

## Risks / Trade-offs

- **A form backend that rejects the value.** The card stays open with the error and the user can answer again; nothing is sent to the agent.
- **A model that still proposes the field.** The prompt rule and the tool result both say not to. The live harness gets a check that "I'd like a loan" ends with the field filled and no second card for it.
