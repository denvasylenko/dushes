# Tasks

## 0. Agree (day 1)
- [x] the client contract with the widget designer (agreed 2026-11-14; see the proposal)
- [ ] QA: the six Vue checks and the HTML scenarios written against this contract (they fail until built)

## 1. Layout and context (backend)
- [x] `repeat` role, the template parsed once, row names `items.N.field`; overlay expands rows from `props[items].rows` and the row keys
- [x] the outline and field cards show the list, its rows and limits; long lists fold
- [x] tests: parsing, expansion, a hash that does not change with rows

## 2. Filling (backend)
- [x] propose_changes accepts row names; `add_row` / `remove_row` with min / max checks; card rows and Undo
- [x] the `rows` capability; without it, no row ops and a clear tool error
- [x] one prompt line on rows (one-based in words, names zero-based); tests

## 3. Clients (widget designer)
- [ ] card rows for add / remove; the HTML bridge (data-repeat, data-row, data-name); `schemaForm` array type; the Vue adapter
- [ ] the card gallery specimens

## 4. Checks and docs
- [ ] QA's Vue checks and HTML scenarios pass; a held-out list form
- [ ] docs: connect-your-form, cards, reference; the spec deltas archived
