## ADDED Requirements

### Requirement: Filling, adding and removing rows
`propose_changes` SHALL accept row names (`items.1.qty`), `{add_row: <container>, index?, values}` and `{remove_row: <container>, index}` (zero-based; every index on a card refers to the form before the card), SHALL respect the container's `min_rows` and `max_rows`, and SHALL show them as rows of the field-change card that the user accepts and can undo; the client SHALL receive `{op: add_row | remove_row, container, index?, values?}`.

#### Scenario: Add a line
- **WHEN** the user says "add two bags of coffee beans" to an order with two lines and room for ten
- **THEN** the card shows "Add a line: Coffee beans × 2", and after it is accepted the form has three lines

#### Scenario: The list is full
- **WHEN** the list already has its `max_rows`
- **THEN** no row is added and the agent says the list is full

### Requirement: Row changes on one card do not conflict
A card that sets a field of a row it also removes SHALL be refused with a tool error; the client SHALL apply set-values first, then removals from the highest index down, then additions, and Undo of a removal SHALL put the row back at its index with its values.

#### Scenario: Undo a removal
- **WHEN** the user accepts "Remove line 2" and then taps Undo
- **THEN** line 2 is back in its place with its values

### Requirement: No row changes without the rows capability
A client that does not list the capability `rows` SHALL get no row ops on cards, and the agent SHALL be told rows cannot be added or removed there and fill only the existing rows.

#### Scenario: An older client
- **WHEN** the client sends capabilities without `rows` and the user asks to add a line
- **THEN** no card offers to add a line, and the agent says lines cannot be added here
