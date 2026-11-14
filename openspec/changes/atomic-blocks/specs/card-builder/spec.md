# Spec Delta

## Purpose
A page on the documentation site where a developer assembles a card from blocks and atoms, sees it drawn live by the real chat widget, and copies it as code or as a card spec.

## ADDED Requirements

### Requirement: Build a card by eye
The docs site SHALL have a page `frontend/card-builder`. It SHALL work without a backend.

On a desktop it SHALL use a canvas wider than the text column, with three columns:
- the palette of every block and atom;
- the card, drawn live by `<agui-chat>`, with an outline of its blocks, items and atoms under it;
- an inspector with a Segmented "Fields | JSON".

On a phone it SHALL stack in this order: the card, a filled "Add" button that opens the palette as a sheet, the outline, then the inspector.

#### Scenario: First visit
- **WHEN** a developer opens the page with nothing in the URL
- **THEN** a starter card ("Our picks" with one primary button) is shown, ready to change, with nothing selected

### Requirement: Add and edit
A block SHALL be added from the palette by a tap, which puts it after the selected block, or by dragging it into the outline or onto the card. An atom SHALL be added the same way into the selected item's `start`, `main` or `end` slot. Selecting in the card or in the outline SHALL select the same thing in both and show its keys as fields. A change SHALL redraw the card within 100 ms.

#### Scenario: A price on the right
- **WHEN** the developer selects an item, taps the `price` atom in the palette and types "CHF 2.50"
- **THEN** the price appears at the right of that row and the JSON shows it in the item's `end`

### Requirement: Move and remove
Reordering SHALL happen in the outline only. Delete or Backspace SHALL remove the selection while focus is in the outline, never in a field, with an Undo pill for about 5 seconds. Reset SHALL return to the starter card with Undo and no confirmation.

#### Scenario: Backspace in a field
- **WHEN** a block is selected and the developer presses Backspace inside one of its fields
- **THEN** only the field's text changes and the block stays

### Requirement: Rows too wide for a phone
An item whose atoms do not fit the card's width at 390 px SHALL show a warning badge on its line in the outline.

#### Scenario: Three badges
- **WHEN** an item holds a long title, three badges and a value
- **THEN** its outline line carries a warning badge and the card still draws it

### Requirement: The JSON edits both ways
The JSON view of the inspector SHALL show the card as it is built. A valid edit SHALL redraw the card. An invalid edit SHALL:
- keep the last good card;
- name the line and the problem under the panel ("Line 12: expected }");
- mark the preview with "Showing the last valid card" until the JSON is valid again.

#### Scenario: A typo in the JSON
- **WHEN** the developer deletes a closing brace
- **THEN** the card stays as it was, a line under the panel names the line of the error and the preview carries the badge

### Requirement: Start from any recipe
A menu SHALL open any card-gallery specimen in the builder, including "Our picks" and "Request sent" as recipes made of the new blocks. The card gallery SHALL have an "Open in builder" link on each specimen.

#### Scenario: Rebuild Request sent
- **WHEN** the developer picks "Request sent" from the menu
- **THEN** the card shows `when`, a guests row and the calendar and directions links, each listed in the outline

### Requirement: Take it away
The page's one main action SHALL be Copy:
- a Segmented "JavaScript | YAML" sits above the code, with one filled Copy button;
- JavaScript is `chat.showCard({...})`;
- YAML is a `formguide.yaml` card spec with the blocks, an empty `data` map and a placeholder `description`.

Light and dark SHALL be a Segmented, and the chat's language a small menu.

The build SHALL be kept in the URL fragment, written without adding history entries, so a copied link opens the same card.

#### Scenario: A shared link
- **WHEN** the developer copies the page URL and opens it in another browser
- **THEN** the same card is shown, with nothing selected

#### Scenario: Many edits
- **WHEN** the developer makes twenty edits and presses Back once
- **THEN** the browser leaves the builder page instead of stepping through the edits
