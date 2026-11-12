# Design

## Mini-brief (ui-craft)
1. **Who and why:** a person fills a long form with the assistant, on a phone or a computer.
2. **Main action:** accept what the assistant offers, in one tap.
3. **Tap ladder:** "Car is a 2019 Toyota Camry" today = chip, card (make, year), card (model) = 3 taps, 3 turns. After: an action chip fills make, year and model = 1 tap, 1 turn. A yes/no question: typing -> 1 tap on a chip.
4. **States:** a chip whose changes fail to apply shows the error under the chips and keeps them; a deferred row whose option is not found is marked "not available" and the rest is applied; a folded card keeps Undo while it lasts.
5. **Phone:** folding keeps the thread short; chips wrap; nothing new on hover.

## Action chips
- The suggestions model gets the form context (field names are in it) and may return `{"text": "...", "set": {"field": value}}` items. Only values the user or the assistant named in the last exchange are allowed (prompt rule).
- `guide.py` validates each `set` against the run's latest config with the same normalisation as `propose_changes` (`_norm_value`, `form_value`) and drops invalid ones, keeping the text.
- Event: `CUSTOM suggestions {items: [str], applies?: [null | [change]]}` aligned by index. `change` has the field-card shape (`name, label, value, display, previous, previous_display`).
- Widget: a chip with changes shows a small ✓ mark; tapping calls `applyChanges`, shows a result line with Undo above the composer flow, then sends the chip text. The next run carries the new form, so the agent sees the change in its diff.

## Deferred rows
- In `propose_changes`, a choice field (dropdown, radio, multiselect) that is disabled or has no options becomes a deferred row when at least one other change in the call is valid: `{name, label, value: null, display: str(value), lookup: str(value), after: [other names], ...previous_of}`.
- The widget applies the other kept rows first, reads the new state's `config.props[name].options`, finds the option by id or label (case-insensitive), encodes it the way the editor does (option object, id or label like the props), and applies it. Not found -> the row shows "not available", and is left out of `names`.
- The resume is the usual `{accepted, config, names?}`; the graph's diff sees both levels.
- Deferred rows come last and carry `deferred: true`. A client that does not know them would apply `value: null`; the widget and the backend ship together (0.x), and CopilotKit-style clients render the card themselves, so they should skip rows with `deferred`.

## Folding
- After a field card is applied, its rows get `hidden`; the result line becomes a button-like summary "✓ Filled in · Make, Year" with Undo; tapping the summary toggles the rows. Rejected cards fold too.
