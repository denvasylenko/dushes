# Spec Delta

## ADDED Requirements

### Requirement: A sortable list
The design system SHALL have a Sortable list primitive, shown on the Design system page. It SHALL reorder like Apple's edit mode:
- rows move by dragging a trailing handle only, so the rest of the row still scrolls on touch;
- on a focused row, Alt with the up or down arrow moves it;
- each row's menu has Move up, Move down and Delete;
- rows may nest one level, as items under a block;
- after each move a polite live region SHALL announce the new position;
- Delete SHALL offer Undo.

#### Scenario: Reorder by keyboard
- **WHEN** focus is on the second of five rows and the reader presses Alt with the down arrow
- **THEN** the row becomes the third and a screen reader hears "Moved to 3 of 5"

#### Scenario: Scrolling on a phone
- **WHEN** a reader swipes up over a row's label, not its handle
- **THEN** the list scrolls and no row moves
