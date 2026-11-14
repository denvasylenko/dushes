# Proposal

## Why

Each of today's 19 blocks fixes one layout. A card that only changes a detail cannot be built, for example a menu line with its description and the price on the right, a service row that opens its times, or a date with a large time. Herefront's old chat had a hand-made card for each of these, and on our blocks they come out worse or are missing. Small atoms placed into the slots of one row would let a developer build these cards, and rebuild them, without a new block each time. A builder on the docs site would let them do it by eye.

## What Changes

- **Containers and atoms.** New blocks `item` and `list`.
  - An `item` is one row with three slots, `start`, `main` and `end`, plus an optional `tap`. A `list` groups items under an optional header.
  - Atoms go into the slots:
    - text: `title`, `subtitle`, `meta`, `badge`, `price`, `value`;
    - images: `icon`, `avatar`, `image`;
    - controls: `chevron`, `check`, `toggle`, `stepper`, `button`;
    - small data: `meter`, `spark`.
  - Shorthand keys on `item` (`title`, `subtitle`, `meta`, `price`, `value`, `chevron`) cover the common rows without slots.
  - `tap` on an item says its text in the chat, opens a link, answers an action like a button, or opens details in place.
  - The controls (`check`, `toggle`, `stepper`) write into the card's values by `name`, like `choice` does.
- **Existing blocks keep their payloads.** `row`, `place` and `steps` are drawn by the same row as `item`, so all lists share one look.
- **New blocks:**
  - `when`: a day line with a large time;
  - `hours` gains `mode: "read"`: a weekly list with "Open now" or "Closed" and today marked;
  - `share`: a link with Copy, or the system's Share;
  - `facts`: rows the user marks Right or edits in place;
  - `checklist`: rows the user ticks;
  - `receipt`: lines, then a total;
  - `rating`: stars, shown or asked;
  - `countdown`: "In 2 h 15 min" up to a moment, then a closing line.
- **A card builder on the docs site** (`frontend/card-builder`):
  - a palette of blocks and atoms, the live card drawn by the real `<agui-chat>` with an outline of its parts, and an inspector with its fields and JSON;
  - add by a tap or by drag, reorder in the outline, edit and remove with Undo;
  - open any card-gallery specimen and rebuild it;
  - one main action, Copy, as `chat.showCard(...)` or as a `formguide.yaml` card spec;
  - the build lives in the URL, so a link shares it.
- The server's card-spec check accepts the new blocks and atom types.

## Capabilities

### New Capabilities
- `card-builder`: the docs-site page where a card is assembled from blocks and atoms, previewed live and exported.

### Modified Capabilities
- `card-blocks`: the `item` and `list` containers, the atoms and their slots, `tap`, the new blocks, and `hours` read mode; the list of known blocks.
- `docs-site`: a Sortable list primitive in the design system.

## Impact

- **Widget:** `packages/agui-chat/src/formguide/blocks.ts`, plus a new `atoms.ts` in the blocks chunk, so the core bundle and its size budget are unchanged. Also `styles.ts`, the texts in `formguide/i18n.ts` and the 6 language packs, and tests in `test/blocks.test.ts`.
- **Backend:** `backend/formguide/cards.py` (`BLOCKS` and the atom check), and `backend/tests/test_cards.py`.
- **Docs:**
  - `frontend/blocks.mdx` gets the atoms, slots and new blocks, and `reference/agui-chat.md` the new block keys.
  - The card gallery `site/src/demo/gallery.ts` gets one specimen per new block, plus "Our picks" and "Request sent" as recipes.
  - The new page `frontend/card-builder.mdx` gets its island.
  - A sortable-list primitive is added to the design system first, with a specimen on `reference/design-system.mdx`.
- **Process:**
  - The design goes to Herefront's Head of Design before code.
  - `ux-review`, `ui-review` and `ux-writer` run before it ships.
  - Herefront's existing cards keep working unchanged.
- **Related changes:**
  - `turn-checklist` is the turn's plan; this `checklist` block is a card the user ticks.
  - The receipt variant of the confirm card in `chat-card-kit` stays its own card; the `receipt` block is a list of priced lines with a total.
