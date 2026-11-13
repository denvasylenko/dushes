## ADDED Requirements

### Requirement: Cards from blocks
The widget SHALL render a card of type `blocks` from its `blocks` list, in order. Known blocks are `title`, `text`, `note`, `row`, `image`, `place`, `stat`, `diff`, `steps`, `progress`, `swatches`, `choice`, `field`, `buttons`, `links` and `divider`; consecutive `row` blocks SHALL form one grouped list. An unknown block SHALL be skipped. Colours SHALL come from the theme and a block's `tone` only.

#### Scenario: A venue card
- **WHEN** a card has a `place` block and a `buttons` block with "Yes, mine" and "No"
- **THEN** the card shows the photo, name and address, and the two buttons, the first one filled

### Requirement: Answering a blocks card
A button with an `id` SHALL resolve the card with `{action, label, values}`, where `values` holds the card's `choice`, `swatches` and `field` values by name, and SHALL fold the card into a result line with the button's label. A `links` entry SHALL open its link, call, route, calendar entry, share sheet or copy its text without resolving the card.

#### Scenario: Picking a palette
- **WHEN** the user taps a swatch named `palette` and then "Use it"
- **THEN** the card resolves with `{action: "use", label: "Use it", values: {palette: "<swatch id>"}}`

### Requirement: Card specs become tools
A card spec (`type`, `description`, `data`, `blocks`, `wait`) in the config SHALL become a model tool `show_<type>` whose parameters are `data`. Calling it SHALL send the card filled from the arguments: as an interrupt that waits for the answer when `wait` is true, else as a `CUSTOM card` event while the turn goes on.

#### Scenario: Is this your barber?
- **WHEN** the model calls `show_barber_match` with a name, a photo and a rating
- **THEN** the chat shows the card filled with them and the turn waits for the answer

### Requirement: Filling a card spec
`{name}` placeholders in the blocks SHALL be filled from the tool's arguments; a placeholder that is the whole value SHALL keep lists and numbers; a block whose `if` names an empty value SHALL be dropped. A spec with an unknown block or a placeholder not in `data` SHALL be refused when the config loads.

#### Scenario: An optional photo
- **WHEN** a `place` block has `if: photo` and the model gives no photo
- **THEN** the card is shown without that block

### Requirement: The answer goes back to the model
The resume of a blocks card SHALL be given to the model as text naming the button (label and id) and the values, or that the user skipped it.

#### Scenario: Yes
- **WHEN** the user taps "Yes, that's my barber" (id `yes`)
- **THEN** the tool result says the user chose "Yes, that's my barber" (yes)

### Requirement: Blocks only for clients that draw them
The card tools SHALL be offered only when the client lists the `blocks` capability, or sends no capability list.

#### Scenario: A client without blocks
- **WHEN** the client's capabilities do not include `blocks`
- **THEN** the model gets no `show_*` card tools
