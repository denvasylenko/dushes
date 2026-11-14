# Design

## Context

- Blocks are drawn in `packages/agui-chat/src/formguide/blocks.ts`, about 390 lines, as one `switch` on `type`.
- The code ships in the on-demand blocks chunk: `agui-chat.blocks.js` next to the one-script build, or its own chunk with a bundler.
- Interactive blocks (`choice`, `swatches`, `field`, `hours`) write into a shared `values` object by `name`, and dispatch `bk-change`. Required ones register into `needs(card)`, which the primary button watches.
- The server validates card specs in `backend/formguide/cards.py` against the `BLOCKS` set.
- The docs site already has:
  - a widget playground (`components/Playground.astro`, page `frontend/playground`);
  - a card gallery (`site/src/demo/gallery.ts`, page `frontend/card-gallery`);
  - a design system in `site/src/components/ui/`, which docs UI must use only.

## Goals / Non-Goals

**Goals:**
- One row anatomy for every list-like line in a card, so a new card is assembled rather than coded.
- A card from before this change draws the same content.
- Building a card takes minutes on the docs page, and the result runs unchanged in `chat.showCard` or `formguide.yaml`.

**Non-Goals:**
- A free layout system: no columns, grids, absolute positions, custom colours or fonts. The card stays an iOS grouped list.
- New model tools. The model still only fills the `data` of a card spec.
- Saving builds on a server. The URL fragment is the only storage.
- Replacing the `chat-card-kit` or `comparison-card` cards.

## Decisions

1. **The tree is fixed: card > block > (list >) item > slot > atom.**
   - *Alternative:* a recursive `stack` or `row` container, where anything goes anywhere. It was rejected:
     - cards would stop looking like one product;
     - the model and the server check would face unbounded shapes;
     - Apple's grouped list, our anchor, is exactly leading, content and trailing.
   - The three slots map to iOS list cells: `start` is the leading accessory, `main` the content, `end` the trailing accessory or detail.

2. **Shorthand first, slots second.**
   - `{title, subtitle, price}` covers most rows and is what the model fills easily. The slots are for the rest.
   - Shorthand atoms come first in their slot, so mixing both stays predictable.

3. **Strings as atoms.** A plain string is a `title` in `main` and a `value` in `end`, so data lists of strings (`["30 €"]`) need no wrapping.

4. **Controls reuse the card's value machinery.**
   - `check`, `toggle` and `stepper` write into `values[name]`, dispatch `bk-change` and register into `needs(card)` when required, exactly like `choice`.
   - So the primary button's "waits for what is required" works with no new rules.

5. **`tap` makes the row the button.**
   - Apple's tappable cell: the whole row presses, and a chevron shows it leads somewhere.
   - A row may not also hold a `button` atom, because two targets in one row break the 44 px rule and confuse touch.
   - `details` opens in place (a disclosure), not as a new card, so there is no card on top of a card.

6. **`row`, `place` and `steps` move onto the item renderer** with an adapter from their payloads.
   - There is one CSS row (`.bk-item`) and one pressed state.
   - The old class names stay on the element (`bk-row`, `bk-place`), so host `::part` and CSS rules keep matching.
   - The `part` names stay too.

7. **Atoms live in a new module `formguide/atoms.ts`** in the blocks chunk. The core IIFE and its 51 KB budget do not grow, while the blocks chunk does.
   - Target: under 8 KB added gzip.
   - Icons for `icon` come from the existing `ICON` set, extended with about 8 symbols: clock, pin, star, person, tag, info, chevron and plus.

8. **New blocks are thin compositions.**
   - `receipt` and `facts` are lists of items with fixed slots.
   - `checklist` is a list of items with a `check` in `start`.
   - `when`, `rating`, `countdown` and `share` are small renderers.
   - `hours` read mode reuses `hoursText()` from `blocks-base.ts` and adds the "open now" calculation, which takes an optional `timezone` through `Intl`.

9. **The builder is an Astro island on its own page.**
   - **Reordering happens in an outline, not on the card.** The card lives in the widget's shadow DOM with its own buttons and controls, so dragging there would fight taps. The outline (like Xcode's navigator or Keynote's layers) lists blocks with their items and atoms nested. A selection in the card or in the outline selects in both, and the card stays a live preview.
   - **Layout.**
     - Desktop: a canvas widened like the gallery's `.cg` (68rem), with three columns: palette | card and outline | inspector. The inspector has a Segmented "Fields | JSON", so JSON gets no pane of its own.
     - Phone: the card, then a filled "Add" button that opens the palette as a sheet (iOS +), then the outline and the inspector.
   - **Copy is the one main action.** A Segmented "JavaScript | YAML" sits above the Code panel with one filled Copy button, so both formats are visible. Recipes go in a Menu, light/dark is a Segmented and the language a small Menu.
   - **A new design-system primitive, Sortable list**, is built by the Docs UX/UI session first (task 4.1) and then used.
     - It follows Apple's edit-mode reorder: a trailing handle, Alt-arrow, a row Menu with Move up, Move down and Delete, a live "Moved to 3 of 5" and Undo on delete.
     - Its props are items, a nested flag, `ui-reorder` and `ui-select`.
     - That session reviews the builder's UI before 4.x is marked done.
   - **JSON errors** keep the last good card, name the line under the panel, and put a "Showing the last valid card" badge on the preview.
   - **Delete and Reset.** Delete or Backspace acts only while focus is in the outline, with an Undo pill for about 5 s. Reset returns to the starter card with Undo.
   - **Width warnings.** The 390 px row-width check shows as a warning Badge on the item's outline line.
   - The live card is a real `<agui-chat mode="inline">` calling `showCard` with `wait: false`.
   - **State.** The build state is the card JSON, compressed into `location.hash` with deflate and base64url, and written with `history.replaceState` debounced to about 300 ms. It holds no personal data, and the selection is cleared on load.
   - The YAML export writes `type`, `description` (a placeholder), an empty `data` and the `blocks`.

10. **The card gallery is the recipe source.** The builder's menu reads `gallery.ts`, so a new specimen is a new recipe with nothing else to update.

## Risks / Trade-offs

- **Moving `row`, `place` and `steps` onto one renderer could shift pixels in Herefront's cards.**
  - Mitigation: before-and-after screenshots of every gallery specimen at 390 px and desktop, light and dark.
  - Herefront's owner is told before release.
- **Atoms make bad layouts possible, such as three badges and two values in one row.**
  - Mitigation: `main` wraps; `end` holds at most two atoms, and the rest are dropped with a console warning.
  - The builder warns about rows wider than the card at 390 px.
- **Drag and drop on touch screens is fragile.** Tap-to-add and Alt-arrow are the primary paths; drag is a convenience.
- **The `countdown` timer runs while the card is on screen.** One shared minute timer serves all countdowns, and it stops when none is connected.
- **Scope.** This is large. Tasks are ordered so atoms and `item`/`list` ship first, the new blocks second and the builder third, each releasable on its own.
