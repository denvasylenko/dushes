# Proposal

## Why

Real forms have dynamic lists: order lines, co-borrowers, previous addresses, children, "add another". The layout today is a fixed tree of named fields, so the agent cannot fill row 3 of a list, add a row or remove one; six checks on QA's Vue stand are paused on this. The CPO decided (2026-11-14) that repeated rows are needed, working for plain HTML and Vue alike.

## What Changes

- **Layout**: a repeat container. In the JSX, `<Repeat name="items">` (any tag mapped to the role `repeat` in `components.containers`) holds a template of fields, written once: `<Repeat name="items"><Input name="product"/><NumberInput name="qty"/></Repeat>`. The layout parses the template once; the jsx_hash does not change when rows are added.
- **Row names**: a row field is addressed `items.0.qty` (container, zero-based row, template field). The config carries the rows as they are now: `props["items"] = {label, min_rows?, max_rows?, row_label?}` and `props["items.0.qty"]`, `state["items.0.qty"]` for each row, plus `props["items"]["rows"]` (the row count) so a page with no values yet still says how many rows it shows. Plain names stay as they are; names never contain a dot today, so nothing existing changes meaning.
- **What the agent sees**: the outline shows the list and each row, `2.3 items Repeat "Order lines" rows 2 of max 10`, then `2.3.1 items.0.product …`, `2.3.2 items.0.qty …` under a row line "row 1". Long lists fold like long sections (the first rows, then "+N rows").
- **Filling**: `propose_changes` takes row names (`items.1.qty`) like any field, and two row changes in the same card: `{"add_row": "items", "values": {"product": "…", "qty": 2}}` (a new row at the end, its values on the same card) and `{"remove_row": "items", "index": 1}`. They respect `min_rows` / `max_rows`, are shown as rows on the field-change card ("Add a line: Coffee beans × 2", "Remove line 2") and are undone like any change. Row numbers in the card and in the agent's replies are one-based ("line 2"), names are zero-based.
- **Clients**: the card's accepted rows go to the form through the adapter, as `{op: "add_row" | "remove_row", container, index?, values?}` next to the set-value changes. HTML forms mark a row with `data-repeat="items" data-row="1"` and fields with `data-name="items.1.qty"`; `schemaForm` gains an `array` field type (`{type: "array", name, fields: [...], min, max}`) that the Vue adapter (`useFormguide`, e.g. over vee-validate's field arrays) and the plain bridge map to the same names. Highlight and "look here" use the same names.
- **Compatibility**: a form without a repeat container sees no change; a client that does not list the capability `rows` gets no add / remove rows on cards (the agent is told rows cannot be added here and fills only existing rows).

## Agreed with the widget designer (2026-11-14)

- `add_row` takes an optional `index` (insert there; default the end); the widget keeps a removed row's values, so Undo of "Remove line 2" is `{op: add_row, container, index: 1, values}`.
- Every index on one card refers to the form before that card. The client applies set-values on existing rows first, then removes from the highest index down, then adds. The server refuses a card that sets a field of a row it also removes.
- The card: "New line 3" as a header with its values as editable rows; "Remove line 2" shows what goes (the row's `row_label`, else its first two values, struck through in the secondary ink with a delete mark, not red); both with the card's Undo. New texts in all seven languages: "New line {n}", "Remove line {n}", "Add a line".
- Plain HTML: the page says how rows are added; the formguide plugin takes `rows: {add(container, index, values), remove(container, index)}` (promises), and the client sends the capability `rows` only when it has that or a `schemaForm` array.
- `schemaForm`: `{type: "array", name, label, fields, min, max, rowLabel?: (values, i) => string}`; FormAccess gains `addRow` and `removeRow`; the Vue adapter maps them to the field array (vee-validate `useFieldArray` push / insert / remove, or a splice on a reactive array).
- Dotted names also mean nested objects (`address.city`): `x.N.y` is a row only when `x` is a declared repeat container.
- Indices are zero-based everywhere in names and attributes (`data-row="0"`, `items.0.qty`), one-based only in words.
- After an add, "look here" targets the new row's first field once it has rendered (the adapter's settle step).

## Capabilities

### Modified Capabilities
- `form-layout`: the repeat container, its template and row names.
- `field-changes`: row names in proposals; adding and removing rows on the field-change card.

## Impact

Backend `form/layout.py`, `form/overlay.py`, `form/render.py`, `agent/tools.py` (propose_changes, the card rows), prompts (one line on rows), the capability `rows`. The widget and adapters (`packages/agui-chat`: card rows, the HTML bridge, `schemaForm` array type, the Vue adapter) by the widget designer. QA: the six Vue-stand checks plus HTML scenarios (fill row 2, add a line, remove a line, max rows). Docs: connect-your-form (the contract), the cards page, the reference. Agreed with the CPO (product) and the widget designer (client contract) before code.
