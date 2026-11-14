# Tasks

## 0. Agreement

- [ ] 0.1 Send proposal and design to Herefront's Head of Design; fold in their notes (one ui-craft and Apple kit for both products)
- [ ] 0.2 Tell Herefront's owner that `row`, `place` and `steps` move onto the item row (same payloads, class and part names kept)

## 1. Atoms, item and list (widget)

- [ ] 1.1 `formguide/atoms.ts`: text atoms (title, subtitle, meta, badge, price, value) and image atoms (icon, avatar, image) with safe URLs; plain strings as title or value
- [ ] 1.2 Extend `ICON` with clock, pin, star, person, tag, info, chevron and plus
- [ ] 1.3 `item` block: the start, main and end slots, the shorthand keys, at most two atoms in `end`, and skipping an empty item
- [ ] 1.4 Controls: check, toggle and stepper writing into `values[name]` with `bk-change` and `needs`; the button atom answering like `buttons`; the chevron
- [ ] 1.5 `tap`: say, link, action (`onAction` first) and details (open in place); the whole row pressable, 44 px on touch, Enter and Space
- [ ] 1.6 `list` block: a title, one inset grouped list, and a `limit` with "Show N more"
- [ ] 1.7 Move `row`, `place` and `steps` onto the item renderer, keeping class and `part` names; check before and after screenshots of every specimen
- [ ] 1.8 Styles in `styles.ts` (`.bk-item`, slots, atoms, pressed state) from tokens only, light and dark
- [ ] 1.9 Texts (`showMore`) in `formguide/i18n.ts` and the 6 packs
- [ ] 1.10 Tests in `test/blocks.test.ts`: shorthand, slots, strings, controls and values, each tap form, list limit, and old cards unchanged

## 2. New blocks (widget)

- [ ] 2.1 `when`: a locale date, a large time, an optional end time and label, and an unparsable date shown as given
- [ ] 2.2 `hours` read mode: joined day runs, Closed, today marked, open now or opens next in local time or `timezone`
- [ ] 2.3 `share`: the system share sheet, or Copy with "Copied" for two seconds, and an optional Open
- [ ] 2.4 `facts`: Right and Edit with a field, Save and Cancel; the value map; `required`
- [ ] 2.5 `checklist`: rows to tick, "{left} left", `required`
- [ ] 2.6 `receipt`: priced items, extra lines and a bold total on one right edge
- [ ] 2.7 `rating`: stars to show, or asked with a name (44 px stars, arrow keys)
- [ ] 2.8 `countdown`: one shared minute timer, a locale duration, `done` and an unparsable time hidden
- [ ] 2.9 Texts (openNow, closedOpens, closed, copied, share, open, right, edit, save, cancel, left, now, inDuration) in English and the 6 packs
- [ ] 2.10 Tests for each new block, and a size check that the blocks chunk grew by less than 8 KB gzip

## 3. Server

- [ ] 3.1 (Owner) `backend/formguide/cards.py`: `BLOCKS` gains item, list, when, share, facts, checklist, receipt, rating and countdown; refuse unknown atoms, a bad `tap`, and a `tap` together with a button atom
- [ ] 3.2 (Owner) `backend/tests/test_cards.py`: valid specs load; each refusal names the card, the block and the problem

## 4. Card builder (docs site)

- [ ] 4.1 Design system (Docs UX/UI session): the Sortable list primitive in `site/src/components/ui/` with a trailing handle, Alt-arrow, a row Menu, nesting, a live position line and Undo; a `ui.css` block, a specimen on `reference/design-system.mdx` and a row in `docs-components.md`
- [ ] 4.2 `frontend/card-builder.mdx` and its island on a 68rem canvas: palette | card and outline | inspector ("Fields | JSON"); on phones the card, an "Add" button opening the palette as a sheet, the outline, then the inspector
- [ ] 4.3 Selection shared by the card and the outline; add by tap, by drag into the outline or onto the card; reorder in the outline; Delete or Backspace only with focus in the outline, with a 5 s Undo pill; Reset with Undo; redraw within 100 ms
- [ ] 4.4 JSON view both ways: an invalid edit keeps the last card, names the line ("Line 12: expected }"), and badges the preview "Showing the last valid card"
- [ ] 4.5 The recipe menu from `gallery.ts`, and "Open in builder" on every gallery specimen
- [ ] 4.6 Copy as the main action, with a Segmented "JavaScript | YAML" and one filled Copy; the state in the URL fragment through `replaceState`, debounced to 300 ms, with the selection cleared on load; a light/dark Segmented and a language Menu
- [ ] 4.7 A warning Badge on outline items too wide at 390 px
- [ ] 4.8 Sidebar entry and "Next" cards linking blocks, gallery and builder
- [ ] 4.9 UI review of 4.2 to 4.8 by the Docs UX/UI session before they are marked done

## 5. Docs and specimens

- [ ] 5.1 `frontend/blocks.mdx`: the item anatomy (with a diagram), the atoms table, tap, the new blocks, and "Every option"
- [ ] 5.2 `reference/agui-chat.md`: the new block and atom keys
- [ ] 5.3 `site/src/demo/gallery.ts`: a specimen per new block, plus "Our picks" and "Request sent" recipes
- [ ] 5.4 `.claude/skills/ui-craft/references/audit.md`: record what this fixes (Herefront cards that came out worse on blocks)
- [ ] 5.5 README: mention the builder next to the playground

## 6. Check and ship

- [ ] 6.1 In the browser at 390 px and 1280 px, light and dark: every new specimen and the builder, keyboard only
- [ ] 6.2 Run the subagents `ux-review`, `ui-review` and `ux-writer`, and fix what they find
- [ ] 6.3 `openspec validate --all --strict`, `python3 scripts/check_english.py`, `cd backend && uv run pytest -q`, `cd packages/agui-chat && npm test`, `cd site && npm run build`
